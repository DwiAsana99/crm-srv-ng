from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.schemas.order import OrderDetailOut, OrderIn, OrderOut, OrderUpdateIn

router = APIRouter()


def _outlet_pad(id_outlet: int) -> str:
    return ("00" + str(id_outlet))[-2:]


async def _last_seq_today(db: AsyncSession, id_outlet: int) -> int:
    res = await db.execute(
        text("""
            SELECT no_order FROM `order`
            WHERE id_outlet = :outlet
              AND DATE(created_date) = CURDATE()
            ORDER BY RIGHT(no_order, 4) DESC
            LIMIT 1
        """),
        {"outlet": id_outlet},
    )
    last = res.scalar()
    return (int(last[-4:]) + 1) if last else 1


async def _harga_efektif(db: AsyncSession, id_outlet: int, barcode: str) -> float:
    res = await db.execute(
        text("""
            SELECT COALESCE(harga_diskon, harga_jual) AS harga
            FROM outlet_item
            WHERE id_outlet = :outlet AND barcode = :barcode
        """),
        {"outlet": id_outlet, "barcode": barcode},
    )
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Item '{barcode}' tidak tersedia di outlet ini",
        )
    return float(row.harga)


@router.post("")
async def add_order(
    payload: OrderIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if str(current_user.role_id) != "4":
        raise HTTPException(status_code=403, detail="Hanya member yang bisa membuat order")

    kode_member = current_user.userable_id
    now = datetime.now()
    yy, mm, dd = now.strftime("%y"), now.strftime("%m"), now.strftime("%d")

    try:
        async with db.begin():
            seq = await _last_seq_today(db, payload.id_outlet)
            noorder = f"{yy}{mm}{dd}{_outlet_pad(payload.id_outlet)}{seq:04d}"

            await db.execute(
                text("""
                    INSERT INTO `order` (no_order, id_outlet, kode_member, tgl_order, total)
                    VALUES (:noorder, :outlet, :member, NOW(), 0)
                """),
                {"noorder": noorder, "outlet": payload.id_outlet, "member": kode_member},
            )

            total = 0.0
            for item in payload.datapesanan:
                harga = await _harga_efektif(db, payload.id_outlet, item.barcode)
                subtot = item.qty * harga
                total += subtot
                await db.execute(
                    text("""
                        INSERT INTO order_detail (no_order, id_outlet, barcode, qty, harga_jual, subtotal)
                        VALUES (:noorder, :outlet, :barcode, :qty, :harga, :subtot)
                    """),
                    {
                        "noorder": noorder,
                        "outlet": payload.id_outlet,
                        "barcode": item.barcode,
                        "qty": item.qty,
                        "harga": harga,
                        "subtot": subtot,
                    },
                )

            await db.execute(
                text("UPDATE `order` SET total = :total WHERE no_order = :noorder"),
                {"total": total, "noorder": noorder},
            )

        return {"message": "Simpan order berhasil", "noorder": noorder}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal simpan order")


@router.put("")
async def update_order(
    payload: OrderUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        async with db.begin():
            res = await db.execute(
                text("SELECT id_outlet FROM `order` WHERE no_order = :noorder"),
                {"noorder": payload.noorder},
            )
            row = res.first()
            if not row:
                raise HTTPException(status_code=404, detail="Order tidak ditemukan")
            id_outlet = int(row.id_outlet)

            await db.execute(
                text("DELETE FROM order_detail WHERE no_order = :noorder"),
                {"noorder": payload.noorder},
            )

            total = 0.0
            for item in payload.datapesanan:
                harga = await _harga_efektif(db, id_outlet, item.barcode)
                subtot = item.qty * harga
                total += subtot
                await db.execute(
                    text("""
                        INSERT INTO order_detail (no_order, id_outlet, barcode, qty, harga_jual, subtotal)
                        VALUES (:noorder, :outlet, :barcode, :qty, :harga, :subtot)
                    """),
                    {
                        "noorder": payload.noorder,
                        "outlet": id_outlet,
                        "barcode": item.barcode,
                        "qty": item.qty,
                        "harga": harga,
                        "subtot": subtot,
                    },
                )

            await db.execute(
                text("UPDATE `order` SET total = :total WHERE no_order = :noorder"),
                {"total": total, "noorder": payload.noorder},
            )

        return {"message": "Simpan order berhasil", "noorder": payload.noorder}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal update order")


@router.get("", response_model=List[OrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if str(current_user.role_id) == "4":
        res = await db.execute(
            text("""
                SELECT `order`.*, member.nama, member.nohp
                FROM `order`
                INNER JOIN member ON `order`.kode_member = member.kode_member
                WHERE member.kode_member = :km AND `order`.status < 4
                ORDER BY `order`.tgl_order DESC
            """),
            {"km": current_user.userable_id},
        )
    else:
        res = await db.execute(
            text("""
                SELECT `order`.*, member.nama, member.nohp
                FROM `order`
                INNER JOIN member ON `order`.kode_member = member.kode_member
                WHERE `order`.status < 4
                ORDER BY `order`.tgl_order DESC
            """)
        )
    return [dict(r) for r in res.mappings().all()]


@router.get("/detail", response_model=List[OrderDetailOut])
async def order_detail(
    noorder: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    res = await db.execute(
        text("""
            SELECT order_detail.*,
                   item.nama_item,
                   item.link_gambar,
                   item.satuan
            FROM order_detail
            INNER JOIN item ON order_detail.barcode = item.barcode
            WHERE order_detail.no_order = :noorder
        """),
        {"noorder": noorder},
    )
    return [dict(r) for r in res.mappings().all()]
