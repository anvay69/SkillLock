import re
from zipfile import BadZipFile
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import UPLOADS
from app.schemas.profile import (
    Certification,
    Education,
    Experience,
    ExtractedProfile,
    ProfileData,
    Project,
)
from app.services.uploads import save_upload


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalized_institution(value: str) -> str:
    return _normalized(DATE_PATTERN.sub("", value))


HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "projects": "projects",
    "personal projects": "projects",
    "work experience": "experience",
    "professional experience": "experience",
    "experience": "experience",
    "employment": "experience",
    "education": "education",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses and certifications": "certifications",
}

DEGREE_PATTERN = re.compile(
    r"\b(?:b\.?\s?sc\.?|b\.?\s?s\.?|b\.?\s?a\.?|bachelor(?:'s)?|"
    r"m\.?\s?sc\.?|m\.?\s?s\.?|m\.?\s?a\.?|"
    r"master(?:'s)?|ph\.?\s?d\.?|doctorate|associate(?:'s)?|diploma)\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


def _read_resume(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if path.suffix.lower() == ".docx":
        document = Document(path)
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        tables = [
            cell.text
            for table in document.tables
            for row in table.rows
            for cell in row.cells
        ]
        return "\n".join([*paragraphs, *tables])
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
        heading = re.sub(r"[:\s]+$", "", line).lower()
        if heading in HEADINGS:
            current = HEADINGS[heading]
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return sections


def _skills(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        line = re.sub(
            r"^(?:programming languages|languages|tools|technologies|frameworks|libraries|"
            r"cloud platforms|databases|technical skills)\s*:\s*",
            "",
            line,
            flags=re.I,
        )
        if len(line) > 160:
            continue
        values = re.split(r"[,;|•·]", line)
        for value in values:
            skill = value.strip(" \t-")
            if 1 < len(skill) <= 48 and not re.search(r"[.!?]", skill):
                result.append(skill)
    return result


def _projects(lines: list[str]) -> list[Project]:
    projects: list[Project] = []
    for line in lines:
        title = _clean_line(line)
        explicit_title = re.match(r"^project\s*:\s*(.+)$", title, re.I)
        if explicit_title:
            title = explicit_title.group(1).strip()
        else:
            continue
        if 3 <= len(title) <= 80 and not re.search(r"[.!?]", title) and not DATE_PATTERN.search(title):
            projects.append(Project(title=title))
    return projects


def _experience(lines: list[str]) -> list[Experience]:
    experiences: list[Experience] = []
    for line in lines:
        line = _clean_line(line)
        parts = re.split(r"\s+(?:\||@|at)\s+", line, maxsplit=2, flags=re.I)
        if len(parts) < 2:
            continue
        title = parts[0].strip(" ,|-")
        company = parts[1].strip(" ,|-")
        if len(parts) == 3:
            company = company.split("|", 1)[0].strip(" ,|-")
        else:
            date_match = DATE_PATTERN.search(company)
            if date_match:
                company = company[:date_match.start()].strip(" ,|-")
        if not title or not company or len(title) > 80 or len(company) > 80:
            continue
        if DATE_PATTERN.search(title) or DATE_PATTERN.search(company):
            continue
        experiences.append(Experience(job_title=title, company=company))
    return experiences


def _education(lines: list[str]) -> list[Education]:
    education: list[Education] = []
    for line in lines:
        line = _clean_line(line)
        if not DEGREE_PATTERN.search(line):
            continue
        parts = re.split(r"\s+(?:at|,|\||—|-)\s+", line, maxsplit=1, flags=re.I)
        degree_field = parts[0]
        degree_match = DEGREE_PATTERN.search(degree_field)
        if not degree_match:
            continue
        degree = line[degree_match.start():degree_match.end()]
        if line[degree_match.end():].startswith("."):
            degree += "."
        field = degree_field[degree_match.end():].strip(" .,:-")
        institution = parts[1].strip() if len(parts) > 1 else ""
        institution = re.sub(r"[, ]+(?:19|20)\d{2}\s*$", "", institution)
        graduation_year = DATE_PATTERN.search(line)
        education.append(
            Education(
                degree=degree,
                field_of_study=field,
                institution=institution,
                graduation_year=graduation_year.group() if graduation_year else "",
            )
        )
    return education


def _certifications(lines: list[str]) -> list[Certification]:
    return [
        Certification(name=_clean_line(line))
        for line in lines
        if 3 <= len(_clean_line(line)) <= 100 and not DATE_PATTERN.fullmatch(_clean_line(line))
    ]


def extract_resume(path: Path) -> ExtractedProfile:
    try:
        sections = _sections(_read_resume(path))
    except (OSError, BadZipFile, PackageNotFoundError, PdfReadError) as error:
        raise ValueError("The uploaded resume could not be read.") from error
    return ExtractedProfile(
        skills=_skills(sections.get("skills", [])),
        projects=_projects(sections.get("projects", [])),
        experience=_experience(sections.get("experience", [])),
        education=_education(sections.get("education", [])),
        certifications=_certifications(sections.get("certifications", [])),
    )


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
                duplicate = bool(key) and any(_normalized(existing.title) == key for existing in current_items)
            elif collection == "experience":
                title = _normalized(item.job_title)
                company = _normalized(item.company)
                duplicate = bool(title) and any(
                    _normalized(existing.job_title) == title
                    and (not company or not _normalized(existing.company) or _normalized(existing.company) == company)
                    for existing in current_items
                )
            elif collection == "education":
                degree = _normalized(item.degree)
                institution = _normalized_institution(item.institution)
                field = _normalized(item.field_of_study)
                duplicate = bool(degree or institution) and any(
                    (degree and _normalized(existing.degree) == degree
                     or institution and _normalized(existing.institution) == institution)
                    and (
                        not institution
                        or not _normalized_institution(existing.institution)
                        or _normalized_institution(existing.institution) == institution
                    )
                    and (not field or not _normalized(existing.field_of_study) or _normalized(existing.field_of_study) == field)
                    for existing in current_items
                )
            else:
                name = _normalized(item.name)
                duplicate = bool(name) and any(_normalized(existing.name) == name for existing in current_items)
            if not duplicate:
                current_items.append(item)
                added_items.append(item)
        added[collection] = added_items

    return updated, ExtractedProfile(**added)


async def store_resume(upload: UploadFile | None) -> tuple[str, ExtractedProfile]:
    if upload is None or not upload.filename:
        return "", ExtractedProfile()
    if Path(upload.filename).suffix.lower() not in {".pdf", ".docx"}:
        raise ValueError("Resume must be a PDF or DOCX file.")

    resume_url = await save_upload(upload)
    try:
        extracted = extract_resume(UPLOADS / Path(resume_url).name)
    except ValueError:
        (UPLOADS / Path(resume_url).name).unlink(missing_ok=True)
        raise
    return resume_url, extracted
