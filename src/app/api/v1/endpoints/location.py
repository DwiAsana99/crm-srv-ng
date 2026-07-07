from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db

router = APIRouter()


@router.get("/kabupaten")
async def get_kabupaten(db: AsyncSession = Depends(get_db)):
    res = await db.execute(text("SELECT * FROM regencies ORDER BY name"))
    return [dict(r) for r in res.mappings().all()]


@router.get("/kecamatan/{kabupaten_id}")
async def get_kecamatan(kabupaten_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        text("SELECT * FROM districts WHERE regency_id = :kid ORDER BY name"),
        {"kid": kabupaten_id},
    )
    return [dict(r) for r in res.mappings().all()]
