from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db

router = APIRouter()


class CommentIn(BaseModel):
    noorder: str
    pesan: str = Field(min_length=1)


@router.post("")
async def add_comment(
    payload: CommentIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    res = await db.execute(
        text("SELECT 1 FROM `order` WHERE no_order = :n"),
        {"n": payload.noorder},
    )
    if not res.scalar():
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    await db.execute(
        text("""
            INSERT INTO order_correspondent (no_order, `by`, role_id, pesan)
            VALUES (:noorder, :by, :role, :pesan)
        """),
        {
            "noorder": payload.noorder,
            "by": current_user.username,
            "role": current_user.role_id,
            "pesan": payload.pesan,
        },
    )
    await db.commit()

    res = await db.execute(
        text("SELECT * FROM order_correspondent WHERE no_order = :n ORDER BY id"),
        {"n": payload.noorder},
    )
    return [dict(r) for r in res.mappings().all()]


@router.get("")
async def list_comments(
    noorder: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    res = await db.execute(
        text("SELECT * FROM order_correspondent WHERE no_order = :n ORDER BY id"),
        {"n": noorder},
    )
    return [dict(r) for r in res.mappings().all()]


@router.get("/aktif")
async def comments_order_aktif(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if str(current_user.role_id) != "4":
        raise HTTPException(status_code=403, detail="Hanya member yang bisa akses endpoint ini")

    kode_member = current_user.userable_id

    res_corr = await db.execute(
        text("""
            SELECT order_correspondent.*
            FROM order_correspondent
            WHERE no_order IN (
                SELECT no_order FROM `order`
                WHERE kode_member = :km AND status < 4
            )
            ORDER BY order_correspondent.id
        """),
        {"km": kode_member},
    )

    res_order = await db.execute(
        text("""
            SELECT no_order, id_outlet, kode_member, tgl_order, total, status
            FROM `order`
            WHERE kode_member = :km AND status < 4
            ORDER BY tgl_order DESC
        """),
        {"km": kode_member},
    )

    return {
        "correspondent": [dict(r) for r in res_corr.mappings().all()],
        "data_order": [dict(r) for r in res_order.mappings().all()],
    }
