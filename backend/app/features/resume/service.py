import logging
import re
import shutil
from pathlib import Path
from uuid import uuid4

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import UploadFile
from pypdf import PdfReader

from app.core.config import PRIVATE_RESUMES, UPLOADS
from app.features.resume.gemini import ResumeGeminiError, extract_resume_profile
from app.schemas.profile import ExtractedProfile, ProfileData

logger = logging.getLogger(__name__)
MAX_RESUME_BYTES = 5 * 1024 * 1024
RESUME_FILE_PREFIX = "/api/me/resume/file/"


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalized_institution(value: str) -> str:
    return _normalized(DATE_PATTERN.sub("", value))


HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "technical proficiencies": "skills",
    "projects": "projects",
    "personal projects": "projects",
    "selected projects": "projects",
    "work experience": "experience",
    "professional experience": "experience",
    "work history": "experience",
    "experience": "experience",
    "employment": "experience",
    "education": "education",
    "academic background": "education",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses and certifications": "certifications",
}

EXCLUDED_HEADINGS = {
    "personal info",
    "personal information",
    "personal details",
    "contact",
    "contact info",
    "contact information",
    "contact details",
    "about me",
    "profile",
    "summary",
    "professional summary",
    "objective",
    "career objective",
    "references",
    "interests",
    "hobbies",
    "awards",
    "publications",
    "activities",
}
DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


def _read_resume(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if path.suffix.lower() == ".docx":
        document = Document(path)
        content = []
        for item in document.iter_inner_content():
            if isinstance(item, Paragraph):
                content.append(item.text)
            elif isinstance(item, Table):
                content.extend(
                    line
                    for row in item.rows
                    for cell in row.cells
                    for line in cell.text.splitlines()
                )
        return "\n".join(content)
    raise ValueError("Resume must be a PDF or DOCX file.")


def _clean_line(line: str) -> str:
    return re.sub(r"^\s*(?:[-*•▪◦‣]|\d+[.)])\s*", "", line).strip()


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue
        line = re.sub(r"\s+", " ", line).strip()
        heading = re.sub(r"[:\s]+$", "", line).lower()
        if heading in HEADINGS:
            current = HEADINGS[heading]
            sections.setdefault(current, [])
        elif heading in EXCLUDED_HEADINGS:
            current = None
        else:
            inline_heading = re.match(r"^([^:|–—-]{2,40})\s*(?::|\||[-–—])\s*(.+)$", line)
            inline_name = inline_heading.group(1).strip().lower() if inline_heading else ""
            if inline_name in HEADINGS:
                current = HEADINGS[inline_name]
                sections.setdefault(current, []).append(inline_heading.group(2).strip())
            elif inline_name in EXCLUDED_HEADINGS:
                current = None
            elif current:
                sections[current].append(line)
    return sections


def extract_resume(path: Path, profile: ProfileData) -> ExtractedProfile:
    try:
        text = _read_resume(path)
    except Exception as error:
        logger.warning("Resume parsing failed (%s).", type(error).__name__)
        raise ValueError("The uploaded resume could not be read.") from error
    if not text.strip():
        raise ValueError(
            "No readable text was found. Use a text-based PDF or a DOCX resume."
        )
    sections = _sections(text)
    return extract_resume_profile(sections, profile)


def add_extracted_profile(
    profile: ProfileData,
    extracted: ExtractedProfile,
) -> tuple[ProfileData, ExtractedProfile]:
    updated = profile.model_copy(deep=True)
    added: dict[str, list] = {}

    existing_skills = {_normalized(skill) for skill in updated.skills}
    added["skills"] = []
    for skill in extracted.skills:
        key = _normalized(skill)
        if key and key not in existing_skills:
            updated.skills.append(skill)
            added["skills"].append(skill)
            existing_skills.add(key)

    collections = ("projects", "experience", "education", "certifications")
    for collection in collections:
        current_items = getattr(updated, collection)
        added_items = []
        for item in getattr(extracted, collection):
            if collection == "projects":
                key = _normalized(item.title)
                duplicate_index = next(
                    (
                        index
                        for index, existing in enumerate(current_items)
                        if key and _normalized(existing.title) == key
                    ),
                    None,
                )
            elif collection == "experience":
                title = _normalized(item.job_title)
                company = _normalized(item.company)
                duplicate_index = next(
                    (
                        index
                        for index, existing in enumerate(current_items)
                        if title
                        and _normalized(existing.job_title) == title
                        and (
                            not company
                            or not _normalized(existing.company)
                            or _normalized(existing.company) == company
                        )
                    ),
                    None,
                )
            elif collection == "education":
                degree = _normalized(item.degree)
                institution = _normalized_institution(item.institution)
                field = _normalized(item.field_of_study)
                duplicate_index = next(
                    (
                        index
                        for index, existing in enumerate(current_items)
                        if (
                            degree and _normalized(existing.degree) == degree
                            or institution
                            and _normalized(existing.institution) == institution
                        )
                        and (
                            not institution
                            or not _normalized_institution(existing.institution)
                            or _normalized_institution(existing.institution) == institution
                        )
                        and (
                            not field
                            or not _normalized(existing.field_of_study)
                            or _normalized(existing.field_of_study) == field
                        )
                    ),
                    None,
                )
            else:
                name = _normalized(item.name)
                duplicate_index = next(
                    (
                        index
                        for index, existing in enumerate(current_items)
                        if name and _normalized(existing.name) == name
                    ),
                    None,
                )
            if duplicate_index is None:
                current_items.append(item)
                added_items.append(item)
            else:
                existing = current_items[duplicate_index]
                merged_values = existing.model_dump()
                for field, value in item.model_dump().items():
                    if not merged_values[field] and value:
                        merged_values[field] = value
                current_items[duplicate_index] = type(existing).model_validate(merged_values)
        added[collection] = added_items

    return updated, ExtractedProfile(**added)


def resume_path(owner_id: int, filename: str) -> Path | None:
    if (
        not filename
        or Path(filename).name != filename
        or Path(filename).suffix.casefold() not in {".pdf", ".docx"}
        or not re.fullmatch(r"[0-9a-f]{32}\.(?:pdf|docx)", filename, re.IGNORECASE)
    ):
        return None
    return PRIVATE_RESUMES / str(owner_id) / filename


def _resume_filename(resume_url: str) -> str | None:
    if not resume_url.startswith(RESUME_FILE_PREFIX):
        return None
    filename = resume_url.removeprefix(RESUME_FILE_PREFIX)
    if "/" in filename or "\\" in filename:
        return None
    if resume_path(0, filename) is None:
        return None
    return filename


async def store_resume(
    upload: UploadFile | None,
    owner_id: int,
    profile: ProfileData,
) -> tuple[str, ExtractedProfile]:
    if upload is None or not upload.filename:
        return "", ExtractedProfile()
    extension = Path(upload.filename).suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise ValueError("Resume must be a PDF or DOCX file.")

    filename = f"{uuid4().hex}{extension}"
    destination = resume_path(owner_id, filename)
    if destination is None:
        raise ValueError("Resume could not be stored.")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        total_size = 0
        with destination.open("xb") as resume_file:
            while chunk := await upload.read(64 * 1024):
                total_size += len(chunk)
                if total_size > MAX_RESUME_BYTES:
                    raise ValueError("Resume must be 5 MB or smaller.")
                resume_file.write(chunk)
        extracted = extract_resume(destination, profile)
    except ValueError:
        destination.unlink(missing_ok=True)
        raise
    except ResumeGeminiError:
        destination.unlink(missing_ok=True)
        raise
    except OSError as error:
        destination.unlink(missing_ok=True)
        raise ValueError("The uploaded resume could not be stored.") from error
    return f"{RESUME_FILE_PREFIX}{filename}", extracted


def promote_staged_resume(resume_url: str, user_id: int) -> str:
    filename = _resume_filename(resume_url)
    if filename is None:
        return resume_url
    staged_path = resume_path(0, filename)
    destination = resume_path(user_id, filename)
    if staged_path is None or destination is None or not staged_path.is_file():
        raise OSError("The staged resume file is unavailable.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staged_path), str(destination))
    return resume_url


def remove_resume(resume_url: str, owner_id: int) -> None:
    filename = _resume_filename(resume_url)
    if filename is not None:
        stored_path = resume_path(owner_id, filename)
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        return
    old_path = legacy_resume_path(resume_url)
    if old_path is not None:
        old_path.unlink(missing_ok=True)


def legacy_resume_path(resume_url: str) -> Path | None:
    prefix = "/uploads/"
    if not resume_url.startswith(prefix):
        return None
    filename = resume_url.removeprefix(prefix)
    if "/" in filename or "\\" in filename:
        return None
    if not re.fullmatch(r"[0-9a-f]{32}\.(?:pdf|docx)", filename, re.IGNORECASE):
        return None
    return UPLOADS / filename
