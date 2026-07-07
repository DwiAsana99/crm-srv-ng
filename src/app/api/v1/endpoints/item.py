import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.schemas.item import ItemOut, ItemOutletOut

router = APIRouter()


@router.get("", response_model=List[ItemOut])
async def get_all_items(db: AsyncSession = Depends(get_db)):
    res = await db.execute(text("SELECT * FROM item ORDER BY nama_item"))
    return [dict(r) for r in res.mappings().all()]


@router.post("", summary="Tambah item (admin)")
async def add_item(
    barcode: str = Form(...),
    nama: str = Form(...),
    satuan: str = Form(...),
    harga: str = Form(...),
    deskripsi: str = Form(default=""),
    kode_kategori_sub: str = Form(...),
    img: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if str(current_user.role_id) != "1":
        raise HTTPException(status_code=403, detail="Hanya admin yang bisa menambah item")

    try:
        harga_val = float(harga)
    except ValueError:
        raise HTTPException(status_code=422, detail="Harga harus berupa angka")

    res = await db.execute(
        text("SELECT 1 FROM item WHERE barcode = :b"),
        {"b": barcode},
    )
    if res.scalar():
        raise HTTPException(status_code=409, detail="Barcode sudah terdaftar")

    link_gambar = ""
    if img:
        item_dir = os.path.join(settings.UPLOAD_DIR, "item")
        os.makedirs(item_dir, exist_ok=True)
        safe_barcode = os.path.basename(barcode)
        dest = os.path.join(item_dir, f"{safe_barcode}.jpg")
        content = await img.read()
        with open(dest, "wb") as f:
            f.write(content)
        link_gambar = dest

    await db.execute(
        text("""
            INSERT INTO item (barcode, nama_item, satuan, harga_jual, link_gambar, deskripsi_item, kode_kategori_sub)
            VALUES (:barcode, :nama, :satuan, :harga, :link_gambar, :deskripsi, :kode_kategori_sub)
        """),
        {
            "barcode": barcode,
            "nama": nama,
            "satuan": satuan,
            "harga": harga_val,
            "link_gambar": link_gambar,
            "deskripsi": deskripsi,
            "kode_kategori_sub": kode_kategori_sub,
        },
    )
    await db.commit()
    return {"message": "Simpan Item berhasil"}


@router.get("/outlet", response_model=List[ItemOutletOut])
async def get_item_outlet(
    outlet_id: int,
    search: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    res = await db.execute(
        text("""
            SELECT outlet_item.barcode,
                   item.nama_item,
                   item.satuan,
                   outlet_item.harga_jual,
                   outlet_item.harga_diskon,
                   item.link_gambar,
                   item.deskripsi_item,
                   item.kode_kategori_sub
            FROM outlet_item
            INNER JOIN item ON outlet_item.barcode = item.barcode
            WHERE outlet_item.id_outlet = :outlet_id
              AND item.nama_item LIKE :search
            ORDER BY item.nama_item
        """),
        {"outlet_id": outlet_id, "search": f"%{search}%"},
    )
    return [dict(r) for r in res.mappings().all()]


@router.get("/outlet/rekomendasi", response_model=List[ItemOutletOut])
async def get_item_outlet_rekomendasi(
    outlet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    res = await db.execute(
        text("""
            SELECT outlet_item.barcode,
                   item.nama_item,
                   item.satuan,
                   outlet_item.harga_jual,
                   outlet_item.harga_diskon,
                   item.link_gambar,
                   item.deskripsi_item,
                   item.kode_kategori_sub
            FROM outlet_item
            INNER JOIN item ON outlet_item.barcode = item.barcode
            WHERE outlet_item.is_rekomendasi = 1
              AND outlet_item.id_outlet = :outlet_id
            ORDER BY item.nama_item
        """),
        {"outlet_id": outlet_id},
    )
    return [dict(r) for r in res.mappings().all()]
