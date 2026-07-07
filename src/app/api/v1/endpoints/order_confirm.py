import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db

router = APIRouter()


async def _correspondent_list(db: AsyncSession, noorder: str) -> list:
    res = await db.execute(
        text("SELECT * FROM order_correspondent WHERE no_order = :n ORDER BY id"),
        {"n": noorder},
    )
    return [dict(r) for r in res.mappings().all()]


async def _assert_order_exists(db: AsyncSession, noorder: str) -> None:
    res = await db.execute(
        text("SELECT 1 FROM `order` WHERE no_order = :n"),
        {"n": noorder},
    )
    if not res.scalar():
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")


@router.post("/reject")
async def confirm_reject(
    noorder: str = Form(...),
    pesan: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _assert_order_exists(db, noorder)
    try:
        async with db.begin():
            await db.execute(
                text("UPDATE `order` SET status = 5 WHERE no_order = :n"),
                {"n": noorder},
            )
            await db.execute(
                text("""
                    INSERT INTO order_correspondent (no_order, `by`, role_id, pesan)
                    VALUES (:noorder, :by, :role, :pesan)
                """),
                {"noorder": noorder, "by": current_user.username,
                 "role": current_user.role_id, "pesan": pesan},
            )
        return await _correspondent_list(db, noorder)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal memproses reject order")


@router.post("/deliver")
async def confirm_deliver(
    noorder: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _assert_order_exists(db, noorder)
    pesan = "Pesanan dikirim oleh admin"
    try:
        async with db.begin():
            await db.execute(
                text("UPDATE `order` SET status = 4 WHERE no_order = :n"),
                {"n": noorder},
            )
            await db.execute(
                text("""
                    INSERT INTO order_correspondent (no_order, `by`, role_id, pesan)
                    VALUES (:noorder, :by, :role, :pesan)
                """),
                {"noorder": noorder, "by": current_user.username,
                 "role": current_user.role_id, "pesan": pesan},
            )
        return await _correspondent_list(db, noorder)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal memproses deliver order")


@router.post("/confirm")
async def confirm_order(
    noorder: str = Form(...),
    ongkir: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _assert_order_exists(db, noorder)
    try:
        ongkir_val = float(ongkir)
    except ValueError:
        raise HTTPException(status_code=422, detail="Ongkir harus berupa angka")

    pesan = "Pesanan dikonfirmasi oleh admin"
    try:
        async with db.begin():
            await db.execute(
                text("""
                    UPDATE `order`
                    SET status = 1, is_confirmed_admin = 1, biaya_ongkir = :ongkir
                    WHERE no_order = :n
                """),
                {"ongkir": ongkir_val, "n": noorder},
            )
            await db.execute(
                text("""
                    INSERT INTO order_correspondent (no_order, `by`, role_id, pesan)
                    VALUES (:noorder, :by, :role, :pesan)
                """),
                {"noorder": noorder, "by": current_user.username,
                 "role": current_user.role_id, "pesan": pesan},
            )
        corr = await _correspondent_list(db, noorder)
        return {"message": {"pesan": corr, "status": 1}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal konfirmasi order")


@router.post("/payment")
async def confirm_payment(
    noorder: str = Form(...),
    img_bukti: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _assert_order_exists(db, noorder)

    # Simpan file bukti bayar — path sandbox dalam UPLOAD_DIR
    safe_noorder = os.path.basename(noorder)
    timestamp = datetime.now().strftime("-%d%m%Y%H%M%S")
    pay_dir = os.path.join(settings.UPLOAD_DIR, "order_payment")
    os.makedirs(pay_dir, exist_ok=True)
    dest = os.path.join(pay_dir, f"{safe_noorder}{timestamp}.jpg")

    content = await img_bukti.read()
    if not content:
        raise HTTPException(status_code=422, detail="File bukti tidak boleh kosong")
    with open(dest, "wb") as f:
        f.write(content)

    pesan = "Bukti bayar telah diunggah, menunggu validasi pembayaran"
    try:
        async with db.begin():
            await db.execute(
                text("UPDATE `order` SET link_gambar_bukti_trf = :path WHERE no_order = :n"),
                {"path": dest, "n": noorder},
            )
            await db.execute(
                text("""
                    INSERT INTO order_correspondent (no_order, `by`, role_id, pesan, link)
                    VALUES (:noorder, :by, :role, :pesan, :link)
                """),
                {"noorder": noorder, "by": current_user.username,
                 "role": current_user.role_id, "pesan": pesan, "link": dest},
            )
        return await _correspondent_list(db, noorder)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal menyimpan bukti bayar")


@router.post("/payment-valid")
async def confirm_payment_valid(
    noorder: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _assert_order_exists(db, noorder)
    pesan = "Pembayaran telah diterima oleh admin"
    try:
        async with db.begin():
            await db.execute(
                text("""
                    UPDATE `order`
                    SET status = 2, is_confirmed_bayar = 1, confirmed_bayar_admin = :admin
                    WHERE no_order = :n
                """),
                {"admin": current_user.username, "n": noorder},
            )
            await db.execute(
                text("""
                    INSERT INTO order_correspondent (no_order, `by`, role_id, pesan)
                    VALUES (:noorder, :by, :role, :pesan)
                """),
                {"noorder": noorder, "by": current_user.username,
                 "role": current_user.role_id, "pesan": pesan},
            )
        corr = await _correspondent_list(db, noorder)
        return {"message": {"pesan": corr, "status": 2}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal validasi pembayaran")
