from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class ItemOut(BaseModel):
    barcode: str
    nama_item: Optional[str] = None
    satuan: Optional[str] = None
    harga_jual: Optional[Decimal] = None
    link_gambar: Optional[str] = None
    deskripsi_item: Optional[str] = None
    kode_kategori_sub: Optional[str] = None

    model_config = {"from_attributes": True}


class ItemIn(BaseModel):
    barcode: str = Field(min_length=1, max_length=50)
    nama: str = Field(min_length=1)
    satuan: str = Field(min_length=1)
    harga: Decimal = Field(gt=0)
    deskripsi: str = ""
    kode_kategori_sub: str = Field(min_length=1)


class ItemOutletOut(BaseModel):
    barcode: str
    nama_item: Optional[str] = None
    satuan: Optional[str] = None
    harga_jual: Optional[Decimal] = None
    harga_diskon: Optional[Decimal] = None
    link_gambar: Optional[str] = None
    deskripsi_item: Optional[str] = None
    kode_kategori_sub: Optional[str] = None

    model_config = {"from_attributes": True}
