from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import UPLOADS


async def save_upload(upload: UploadFile | None) -> str:
    if upload is None or not upload.filename:
        return ""
    UPLOADS.mkdir(exist_ok=True)
    filename = f"{uuid4().hex}{Path(upload.filename).suffix[:12]}"
    (UPLOADS / filename).write_bytes(await upload.read())
    return f"/uploads/{filename}"
