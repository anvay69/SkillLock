from fastapi import APIRouter

from app.services.users import list_skills


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[str])
def get_skills() -> list[str]:
    return list_skills()
