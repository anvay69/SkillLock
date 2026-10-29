import re

from app.models.user import User
from app.schemas.job_matching import JobMatchResponse
from app.schemas.profile import ProfileData
from app.services.users import list_skills


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for comparison."""
    return re.sub(r"[^a-z0-9#+.]+", " ", text.casefold()).strip()


def _extract_jd_skills(jd_text: str, known_skills: list[str]) -> list[str]:
    """Find skills mentioned in the job description.

    Strategy:
    1. Match against the global skills catalog (case-insensitive).
    2. Also pick up common tech keywords that may not be in the catalog yet.
    """
    normalized_jd = _normalize(jd_text)
    found: dict[str, str] = {}  # normalized -> original display name

    # Match against known skill catalog
    for skill in known_skills:
        key = _normalize(skill)
        if not key:
            continue
        # Use word-boundary matching so "java" doesn't match "javascript"
        pattern = r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])"
        if re.search(pattern, normalized_jd):
            found[key] = skill

    # Also try to pick up requirement-list items from the JD itself
    # Common patterns: "Proficient in X", "Experience with X", bullet lists
    requirement_patterns = [
        r"(?:proficien(?:t|cy)|knowledge|familiar(?:ity)?|expertise|skilled|hands[- ]on)"
        r"\s+(?:in|with|of|using)\s+([A-Za-z0-9#+./_ ,&]+)",
    ]
    for pattern in requirement_patterns:
        for match in re.finditer(pattern, jd_text, re.IGNORECASE):
            tokens = re.split(r"[,;|•·]", match.group(1))
            for token in tokens:
                clean = token.strip(" \t-")
                key = _normalize(clean)
                if 2 <= len(key) <= 48 and key not in found and len(key.split()) <= 4:
                    found[key] = clean

    # Pick up bullet-list items (lines starting with - or •)
    for line in jd_text.splitlines():
        line = line.strip()
        bullet_match = re.match(r"^[-*•▪◦‣]\s+(.+)$", line)
        if not bullet_match:
            continue
        # Extract short skill-like tokens from bullet items
        tokens = re.split(r"[,;|•·]", bullet_match.group(1))
        for token in tokens:
            clean = token.strip(" \t-")
            key = _normalize(clean)
            # Only add short, skill-like phrases (1-4 words, no sentences)
            # Skip if a catalog skill already covers this token
            already_covered = any(
                existing in key or key in existing for existing in found
            )
            if (
                2 <= len(key) <= 48
                and key not in found
                and not already_covered
                and len(key.split()) <= 4
                and not re.search(r"[.!?]", clean)
            ):
                found[key] = clean

    return list(found.values())


def _build_profile(user: User) -> ProfileData:
    """Reconstruct a ProfileData from user row."""
    return ProfileData.model_validate(
        {
            **user.profile,
            "name": user.name,
            "username": user.username,
            "email": user.email,
        }
    )


def analyze_job_match(user: User, jd_text: str) -> JobMatchResponse:
    """Compare extracted JD skills against candidate profile."""
    profile = _build_profile(user)
    known_skills = list_skills()
    jd_skills = _extract_jd_skills(jd_text, known_skills)

    if not jd_skills:
        return JobMatchResponse(
            feedback="Could not identify specific skills from the job description. "
            "Try pasting the full requirements section.",
        )

    # Normalize candidate skills for comparison
    candidate_skill_map: dict[str, str] = {}
    for skill in profile.skills:
        candidate_skill_map[_normalize(skill)] = skill

    # Also count skills implied by projects and experience
    for project in profile.projects:
        for token in re.split(r"[,;|•·/]", project.tech_stack):
            clean = token.strip()
            if clean:
                candidate_skill_map.setdefault(_normalize(clean), clean)

    matched: list[str] = []
    missing: list[str] = []

    for jd_skill in jd_skills:
        key = _normalize(jd_skill)
        if key in candidate_skill_map:
            matched.append(candidate_skill_map[key])
        else:
            missing.append(jd_skill)

    total = len(matched) + len(missing)
    readiness = round(len(matched) / total * 100) if total else 0

    # Generate feedback
    if readiness >= 80:
        feedback = (
            f"Strong match! You meet {readiness}% of the identified skill requirements. "
            "You should be well positioned for this role."
        )
    elif readiness >= 50:
        feedback = (
            f"Moderate match at {readiness}%. You have a solid foundation but there are "
            "some gaps to address before applying."
        )
    else:
        feedback = (
            f"Currently at {readiness}% match. Consider building the missing skills through "
            "courses, projects, or certifications before applying."
        )

    # Generate suggestions
    suggestions: list[str] = []
    if missing:
        top_missing = missing[:5]
        suggestions.append(
            f"Focus on learning: {', '.join(top_missing)}."
        )
    if missing and profile.projects:
        suggestions.append(
            "Add a project using some of the missing skills to strengthen your profile."
        )
    if missing and not profile.certifications:
        suggestions.append(
            "Consider earning certifications in key missing areas to stand out."
        )
    if readiness >= 70 and missing:
        suggestions.append(
            "You're close — highlight transferable experience in your resume to bridge the remaining gaps."
        )

    return JobMatchResponse(
        matched_skills=matched,
        missing_skills=missing,
        readiness_percent=readiness,
        feedback=feedback,
        suggestions=suggestions,
    )

