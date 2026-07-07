from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class PesananItem(BaseModel):
    barcode: str
    qty: int = Field(gt=0)


class OrderIn(BaseModel):
    id_outlet: int
    datapesanan: List[PesananItem] = Field(min_length=1)


class OrderUpdateIn(BaseModel):
    noorder: str
    datapesanan: List[PesananItem] = Field(min_length=1)


class OrderOut(BaseModel):
    no_order: str
    id_outlet: Optional[int] = None
    kode_member: Optional[str] = None
    tgl_order: Optional[datetime] = None
    total: Optional[Decimal] = None
    status: Optional[int] = None
    nama: Optional[str] = None
    nohp: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderDetailOut(BaseModel):
    no_order: str
    barcode: str
    qty: Optional[int] = None
    harga_jual: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    nama_item: Optional[str] = None
    link_gambar: Optional[str] = None
    satuan: Optional[str] = None

    model_config = {"from_attributes": True}
