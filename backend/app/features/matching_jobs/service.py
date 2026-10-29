import json
import re

from app.core.database import database
from app.models.user import User
from app.schemas.matching_jobs import (
    JobDetail,
    JobSummary,
    MatchedSkillInfo,
    SavedJobResponse,
)
from app.schemas.profile import ProfileData


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for comparison."""
    return re.sub(r"[^a-z0-9#+.]+", " ", text.casefold()).strip()


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


def _candidate_skills(user: User) -> dict[str, str]:
    """Build a normalized -> display name map of all candidate skills."""
    profile = _build_profile(user)
    skill_map: dict[str, str] = {}
    for skill in profile.skills:
        skill_map[_normalize(skill)] = skill
    # Include tech stacks from projects
    for project in profile.projects:
        for token in re.split(r"[,;|•·/]", project.tech_stack):
            clean = token.strip()
            if clean:
                skill_map.setdefault(_normalize(clean), clean)
    return skill_map


def _match_skills(
    required_skills: list[str], candidate_skill_map: dict[str, str]
) -> MatchedSkillInfo:
    """Compare required job skills against candidate skills."""
    matched: list[str] = []
    missing: list[str] = []
    for skill in required_skills:
        key = _normalize(skill)
        if key in candidate_skill_map:
            matched.append(candidate_skill_map[key])
        else:
            missing.append(skill)
    total = len(matched) + len(missing)
    percent = round(len(matched) / total * 100) if total else 0
    return MatchedSkillInfo(
        matched_skills=matched,
        missing_skills=missing,
        match_percent=percent,
    )


def _match_explanation(match: MatchedSkillInfo, title: str) -> str:
    """Generate a human-readable explanation for the match."""
    pct = match.match_percent
    if pct >= 80:
        feedback = (
            f"Strong match for {title}! You meet {pct}% of the skill requirements. "
            "You should be well positioned to apply."
        )
    elif pct >= 50:
        feedback = (
            f"Moderate match for {title} at {pct}%. You have a solid foundation "
            "but there are some skill gaps to work on."
        )
    else:
        feedback = (
            f"Currently at {pct}% match for {title}. Consider building the missing "
            "skills before applying."
        )
    if match.missing_skills:
        top = ", ".join(match.missing_skills[:5])
        feedback += f" Focus areas: {top}."
    return feedback


def _saved_job_ids(user_id: int) -> set[str]:
    """Return the set of job IDs saved by this user."""
    with database() as db:
        rows = db.execute(
            "SELECT job_id FROM saved_jobs WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row["job_id"] for row in rows}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_matched_jobs(user: User) -> list[JobSummary]:
    """List all jobs ranked by match percentage for the candidate."""
    skill_map = _candidate_skills(user)
    with database() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY title").fetchall()

    results: list[tuple[int, JobSummary]] = []
    for row in rows:
        required = json.loads(row["required_skills_json"])
        match = _match_skills(required, skill_map)
        results.append(
            (
                match.match_percent,
                JobSummary(
                    id=row["id"],
                    title=row["title"],
                    company=row["company"],
                    location=row["location"],
                    job_type=row["job_type"],
                    match=match,
                ),
            )
        )

    # Sort by match percentage descending (best matches first)
    results.sort(key=lambda pair: pair[0], reverse=True)
    return [summary for _, summary in results]


def get_matched_job(user: User, job_id: str) -> JobDetail:
    """Return full job details with match explanation."""
    with database() as db:
        row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None  # type: ignore[return-value]

    skill_map = _candidate_skills(user)
    required = json.loads(row["required_skills_json"])
    match = _match_skills(required, skill_map)
    saved_ids = _saved_job_ids(user.id)

    return JobDetail(
        id=row["id"],
        title=row["title"],
        company=row["company"],
        location=row["location"],
        job_type=row["job_type"],
        description=row["description"],
        required_skills=required,
        match=match,
        explanation=_match_explanation(match, row["title"]),
        is_saved=row["id"] in saved_ids,
    )


def list_saved_jobs(user: User) -> list[JobSummary]:
    """List the candidate's saved/bookmarked jobs."""
    skill_map = _candidate_skills(user)
    with database() as db:
        rows = db.execute(
            """SELECT jobs.* FROM saved_jobs
               JOIN jobs ON jobs.id = saved_jobs.job_id
               WHERE saved_jobs.user_id = ?
               ORDER BY jobs.title""",
            (user.id,),
        ).fetchall()

    results: list[JobSummary] = []
    for row in rows:
        required = json.loads(row["required_skills_json"])
        match = _match_skills(required, skill_map)
        results.append(
            JobSummary(
                id=row["id"],
                title=row["title"],
                company=row["company"],
                location=row["location"],
                job_type=row["job_type"],
                match=match,
            )
        )
    return results


def save_job(user: User, job_id: str) -> SavedJobResponse:
    """Save/bookmark a job for the candidate. Idempotent."""
    with database() as db:
        # Verify job exists
        job = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            return None  # type: ignore[return-value]
        db.execute(
            "INSERT OR IGNORE INTO saved_jobs (user_id, job_id) VALUES (?, ?)",
            (user.id, job_id),
        )
    return SavedJobResponse(ok=True, job_id=job_id, saved=True)


def unsave_job(user: User, job_id: str) -> SavedJobResponse:
    """Remove a saved job for the candidate."""
    with database() as db:
        db.execute(
            "DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?",
            (user.id, job_id),
        )
    return SavedJobResponse(ok=True, job_id=job_id, saved=False)

