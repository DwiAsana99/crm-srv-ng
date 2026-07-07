from pydantic import BaseModel, EmailStr, Field
from datetime import date


class MessageOnly(BaseModel):
    message: str


class LoginIn(BaseModel):
    username: str
    password: str


class RegistrationIn(BaseModel):
    nama_lengkap: str = Field(min_length=1)
    email: EmailStr
    no_hp: str = Field(min_length=6, max_length=20)
    instagram: str
    tgl_lahir: date
    jkel: str = Field(pattern="^[LP]$")
    kata_sandi: str = Field(min_length=8, max_length=512)
    kata_sandi_konfirm: str
    alamat: str
    kabupaten: int
    kecamatan: int
    token_fcm: str


class OtpVerifyIn(BaseModel):
    otp_token: str
    otp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
