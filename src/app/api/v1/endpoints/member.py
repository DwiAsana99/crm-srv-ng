from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.schemas.member import MemberOut, MemberUpdateIn

router = APIRouter()


@router.get("/{kode_member}", response_model=MemberOut)
async def get_profil(kode_member: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        text("SELECT * FROM member WHERE kode_member = :km"),
        {"km": kode_member},
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Member tidak ditemukan")
    return dict(row)


@router.put("", summary="Update profil member")
async def update_profil(
    payload: MemberUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if str(current_user.role_id) != "4":
        raise HTTPException(status_code=403, detail="Hanya member yang bisa update profil")

    if current_user.userable_id != payload.kode_member:
        raise HTTPException(status_code=403, detail="Tidak bisa update profil member lain")

    res = await db.execute(
        text("SELECT 1 FROM member WHERE kode_member = :km"),
        {"km": payload.kode_member},
    )
    if not res.scalar():
        raise HTTPException(status_code=404, detail="Member tidak ditemukan")

    await db.execute(
        text("""
            UPDATE member
               SET nama       = :nama,
                   jk         = :jk,
                   email      = :email,
                   alamat     = :alamat,
                   kabupaten  = :kabupaten,
                   kecamatan  = :kecamatan,
                   nohp       = :nohp,
                   instagram  = :instagram,
                   tgllahir   = :tgllahir
             WHERE kode_member = :kode_member
        """),
        {
            "nama": payload.nama_lengkap,
            "jk": payload.jkel,
            "email": str(payload.email),
            "alamat": payload.alamat,
            "kabupaten": payload.kabupaten,
            "kecamatan": payload.kecamatan,
            "nohp": payload.no_hp,
            "instagram": payload.instagram,
            "tgllahir": payload.tgl_lahir,
            "kode_member": payload.kode_member,
        },
    )
    await db.commit()
    return {"message": "Ubah Profil berhasil"}
