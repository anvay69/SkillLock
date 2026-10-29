import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)


MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_DESCRIPTION_LENGTH = 20_000
FETCH_TIMEOUT_SECONDS = 8
MAX_REDIRECTS = 3
PUBLIC_LISTING_MESSAGE = (
    "LinkedIn did not provide readable public job details. "
    "Paste the job description text and try again."
)


class LinkedInFetchError(ValueError):
    pass


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class _VisibleTextParser(HTMLParser):
    _BLOCK_ELEMENTS = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "li",
        "p",
        "section",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_ELEMENTS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self._BLOCK_ELEMENTS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


class _ListingMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metadata: dict[str, str] = {}
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.casefold(): value or "" for key, value in attrs}
        if tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            value = attributes.get("content")
            if key and value:
                self.metadata[key.casefold()] = value
        elif tag == "script" and attributes.get("type", "").casefold() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_ld_parts))
            self._json_ld_parts = []
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_parts.append(data)


def _validate_public_listing_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise LinkedInFetchError("Enter a valid LinkedIn job listing URL.") from error

    linkedin_listing_path = bool(
        re.fullmatch(r"/jobs/view/[A-Za-z0-9%._~-]+/?", parsed.path)
        or re.fullmatch(r"/posts/[A-Za-z0-9%._~-]+/?", parsed.path)
    )
    short_link_path = bool(re.fullmatch(r"/p/[A-Za-z0-9_-]+/?", parsed.path))
    allowed_host = (
        hostname is not None
        and (
            hostname.casefold() in {"linkedin.com", "www.linkedin.com"}
            and linkedin_listing_path
            or hostname.casefold() == "lnkd.in"
            and short_link_path
        )
    )
    if (
        parsed.scheme.casefold() != "https"
        or not allowed_host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise LinkedInFetchError(
            "Enter a public LinkedIn job or post URL, or an lnkd.in/p/... short link."
        )


def _job_postings(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [posting for item in value for posting in _job_postings(item)]
    if not isinstance(value, dict):
        return []

    postings: list[dict[str, object]] = []
    item_type = value.get("@type", [])
    types = item_type if isinstance(item_type, list) else [item_type]
    if any(isinstance(item, str) and item.casefold() == "jobposting" for item in types):
        postings.append(value)
    graph = value.get("@graph")
    if graph is not None:
        postings.extend(_job_postings(graph))
    return postings


def _plain_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parser = _VisibleTextParser()
    parser.feed(unescape(value))
    return " ".join(" ".join(parser.parts).split())[:MAX_DESCRIPTION_LENGTH]


def _extract_listing(html: str) -> dict[str, str]:
    parser = _ListingMetadataParser()
    parser.feed(html)
    page_text = _plain_text(html)

    title = parser.metadata.get("og:title", "")
    company = ""
    description = ""
    for raw_json in parser.json_ld:
        try:
            data = json.loads(raw_json)
        except ValueError:
            continue
        postings = _job_postings(data)
        if not postings:
            continue
        posting = postings[0]
        title = str(posting.get("title") or title)
        description = _plain_text(posting.get("description"))
        organization = posting.get("hiringOrganization")
        if isinstance(organization, dict):
            company = str(organization.get("name") or "")
        if description:
            break

    if not description:
        description = (
            _plain_text(parser.metadata.get("og:description"))
            or _plain_text(parser.metadata.get("description"))
        )
    if description and _normalized_text(description) not in _normalized_text(page_text):
        page_text = f"{page_text} {description}".strip()
    return {
        "job_title": title.strip()[:300],
        "company": company.strip()[:200],
        "job_description": description,
        "page_text": page_text[:MAX_DESCRIPTION_LENGTH],
    }


def _normalized_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def fetch_linkedin_job(url: str) -> dict[str, str]:
    _validate_public_listing_url(url)
    opener = build_opener(ProxyHandler({}), _NoRedirectHandler())
    current_url = url
    visited_urls: set[str] = set()
    body = b""
    content_type = ""
    for redirect_count in range(MAX_REDIRECTS + 1):
        _validate_public_listing_url(current_url)
        if current_url in visited_urls:
            raise LinkedInFetchError("LinkedIn returned a redirect loop. Use a direct public listing URL.")
        visited_urls.add(current_url)
        request = Request(
            current_url,
            headers={
                "Accept": "text/html",
                "Accept-Encoding": "identity",
                "User-Agent": "SkillLock public job listing analyzer/1.0",
            },
        )
        try:
            response = opener.open(request, timeout=FETCH_TIMEOUT_SECONDS)
        except HTTPError as error:
            if 300 <= error.code < 400:
                location = error.headers.get("Location")
                error.close()
                if not location or redirect_count >= MAX_REDIRECTS:
                    raise LinkedInFetchError(
                        "LinkedIn redirected this request too many times. Use a direct public listing URL."
                    ) from error
                current_url = urljoin(current_url, location)
                continue
            raise LinkedInFetchError(PUBLIC_LISTING_MESSAGE) from error
        except (TimeoutError, URLError, OSError) as error:
            raise LinkedInFetchError(
                "Could not retrieve this public LinkedIn listing. Paste the job description and try again."
            ) from error

        with response:
            if 300 <= response.status < 400:
                location = response.headers.get("Location")
                if not location or redirect_count >= MAX_REDIRECTS:
                    raise LinkedInFetchError(
                        "LinkedIn redirected this request too many times. Use a direct public listing URL."
                    )
                current_url = urljoin(current_url, location)
                continue
            if response.status != 200:
                raise LinkedInFetchError(PUBLIC_LISTING_MESSAGE)
            content_type = response.headers.get_content_type()
            if content_type != "text/html":
                raise LinkedInFetchError(PUBLIC_LISTING_MESSAGE)
            body = response.read(MAX_PAGE_BYTES + 1)
            break

    if len(body) > MAX_PAGE_BYTES:
        raise LinkedInFetchError(PUBLIC_LISTING_MESSAGE)
    page = _extract_listing(body.decode("utf-8", errors="replace"))
    if not page["page_text"]:
        raise LinkedInFetchError(PUBLIC_LISTING_MESSAGE)
    return page
