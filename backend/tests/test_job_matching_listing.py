import unittest
from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from app.features.job_matching import listing
from app.schemas.job_matching import JobMatchRequest


class FakeResponse(BytesIO):
    status = 200

    def __init__(self, content: bytes, content_type: str = "text/html") -> None:
        super().__init__(content)
        self.headers = Message()
        self.headers["Content-Type"] = content_type


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.request = None

    def open(self, request, timeout: int) -> FakeResponse:
        self.request = request
        return self.response


class SequenceOpener:
    def __init__(self, outcomes: list[FakeResponse | HTTPError]) -> None:
        self.outcomes = outcomes
        self.requests = []

    def open(self, request, timeout: int) -> FakeResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, HTTPError):
            raise outcome
        return outcome


class LinkedInListingTests(unittest.TestCase):
    def test_fetches_and_extracts_public_job_posting_data(self) -> None:
        page = b"""
        <html><head><script type="application/ld+json">
        {"@type":"JobPosting","title":"Backend Engineer",
         "hiringOrganization":{"name":"Example Co"},
         "description":"&lt;p&gt;Python and Docker are required.&lt;/p&gt;"}
        </script></head></html>
        """
        opener = FakeOpener(FakeResponse(page))
        with patch.object(listing, "build_opener", return_value=opener):
            result = listing.fetch_linkedin_job(
                "https://www.linkedin.com/jobs/view/123456/"
            )

        self.assertEqual(result["job_title"], "Backend Engineer")
        self.assertEqual(result["company"], "Example Co")
        self.assertEqual(result["job_description"], "Python and Docker are required.")
        self.assertIn("Python and Docker are required.", result["page_text"])
        self.assertNotIn("Cookie", opener.request.headers)

    def test_falls_back_to_public_metadata_description(self) -> None:
        page = b"""
        <html><head>
        <meta property="og:title" content="Engineer at Sample Co">
        <meta property="og:description" content="Work with React and SQL.">
        </head></html>
        """
        opener = FakeOpener(FakeResponse(page))
        with patch.object(listing, "build_opener", return_value=opener):
            result = listing.fetch_linkedin_job(
                "https://www.linkedin.com/jobs/view/123456"
            )

        self.assertEqual(result["job_title"], "Engineer at Sample Co")
        self.assertEqual(result["job_description"], "Work with React and SQL.")
        self.assertIn("Work with React and SQL.", result["page_text"])

    def test_rejects_non_linkedin_hosts_and_non_job_paths_before_fetch(self) -> None:
        for url in (
            "https://linkedin.com.evil.example/jobs/view/123",
            "https://www.linkedin.com/feed/",
            "https://lnkd.in/other/123",
            "https://127.0.0.1/jobs/view/123",
        ):
            with self.subTest(url=url), patch.object(listing, "build_opener") as build_opener:
                with self.assertRaises(listing.LinkedInFetchError):
                    listing.fetch_linkedin_job(url)
                build_opener.assert_not_called()

    def test_resolves_short_link_only_to_allowed_linkedin_post(self) -> None:
        headers = Message()
        headers["Location"] = "https://www.linkedin.com/posts/example_job-opening-123/"
        redirect = HTTPError(
            "https://lnkd.in/p/example",
            302,
            "Redirect",
            headers,
            None,
        )
        page = FakeResponse(
            b'<html><head><meta property="og:description" content="React and JavaScript required."></head>'
            b"<body>Frontend Developer Intern at Zuperr.</body></html>"
        )
        opener = SequenceOpener([redirect, page])
        with patch.object(listing, "build_opener", return_value=opener):
            result = listing.fetch_linkedin_job("https://lnkd.in/p/example")
        self.assertIn("Frontend Developer Intern", result["page_text"])
        self.assertIn("React and JavaScript required.", result["page_text"])
        self.assertEqual(len(opener.requests), 2)

    def test_rejects_short_link_redirect_outside_allowed_linkedin_paths(self) -> None:
        headers = Message()
        headers["Location"] = "https://example.com/collect"
        redirect = HTTPError(
            "https://lnkd.in/p/example",
            302,
            "Redirect",
            headers,
            None,
        )
        opener = SequenceOpener([redirect])
        with patch.object(listing, "build_opener", return_value=opener):
            with self.assertRaisesRegex(listing.LinkedInFetchError, "public LinkedIn"):
                listing.fetch_linkedin_job("https://lnkd.in/p/example")
        self.assertEqual(len(opener.requests), 1)

    def test_request_schema_accepts_job_posts_and_short_links(self) -> None:
        for url in (
            "https://lnkd.in/p/eT7YsB-z",
            "https://www.linkedin.com/posts/example_job-opening-123/",
            "https://www.linkedin.com/jobs/view/123456",
        ):
            with self.subTest(url=url):
                request = JobMatchRequest(linkedin_url=url)
                self.assertEqual(request.linkedin_url, url)

    def test_request_schema_restricts_short_links_to_post_paths(self) -> None:
        for url in (
            "https://lnkd.in/jobs/view/123456",
            "https://lnkd.in/posts/example_job-opening-123",
            "https://www.linkedin.com/p/eT7YsB-z",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                JobMatchRequest(linkedin_url=url)


if __name__ == "__main__":
    unittest.main()
