from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional


class MemberOut(BaseModel):
    kode_member: str
    nama: Optional[str] = None
    jk: Optional[str] = None
    email: Optional[str] = None
    alamat: Optional[str] = None
    kabupaten: Optional[int] = None
    kecamatan: Optional[int] = None
    nohp: Optional[str] = None
    instagram: Optional[str] = None
    tgllahir: Optional[date] = None
    profile_photo: Optional[str] = None
    poin: Optional[int] = None

    model_config = {"from_attributes": True}


class MemberUpdateIn(BaseModel):
    kode_member: str
    nama_lengkap: str = Field(min_length=1)
    email: EmailStr
    no_hp: str = Field(min_length=6, max_length=20)
    instagram: str
    tgl_lahir: date
    jkel: str = Field(pattern="^[LP]$")
    alamat: str
    kabupaten: int
    kecamatan: int
