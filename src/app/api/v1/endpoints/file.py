import mimetypes
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter()

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.get("/img")
async def serve_image(path: str):
    upload_root = os.path.abspath(settings.UPLOAD_DIR)

    # Resolve requested path — block traversal (e.g. ../../etc/passwd)
    requested = os.path.abspath(os.path.join(upload_root, path))
    if not requested.startswith(upload_root + os.sep) and requested != upload_root:
        raise HTTPException(status_code=403, detail="Akses tidak diizinkan")

    ext = os.path.splitext(requested)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Tipe file tidak diizinkan")

    if not os.path.isfile(requested):
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    mime, _ = mimetypes.guess_type(requested)
    return FileResponse(requested, media_type=mime or "application/octet-stream")
