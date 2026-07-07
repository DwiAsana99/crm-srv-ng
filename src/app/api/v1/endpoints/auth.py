import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.fonnte import send_whatsapp
from app.core.limiter import limiter
from app.core.security import ALGO, create_access_token, create_bsha256, verify_password
from app.deps.db import get_db
from app.schemas.auth import MessageOnly, OtpVerifyIn, RegistrationIn

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _read_credentials(req: Request) -> tuple[str, str]:
    ctype = (req.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
        form = await req.form()
        return (str(form.get("username") or ""), str(form.get("password") or ""))
    data = await req.json()
    return (str(data.get("username") or ""), str(data.get("password") or ""))


def _otp_hash(otp: str) -> str:
    """HMAC-style hash: sha256(otp + SECRET_KEY). Tidak reversible dari JWT payload."""
    return hashlib.sha256(f"{otp}{settings.SECRET_KEY}".encode()).hexdigest()


def _make_otp_token(otp: str, reg_data: dict) -> str:
    """
    JWT pendek (OTP_EXPIRE_MINUTES) berisi:
    - otp_hash: untuk verifikasi tanpa expose OTP
    - reg: data registrasi lengkap supaya verify endpoint stateless
    """
    payload = {
        "sub": "otp_reg",
        "otp_hash": _otp_hash(otp),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        "reg": reg_data,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGO)


def _decode_otp_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        if payload.get("sub") != "otp_reg":
            raise ValueError
        return payload
    except (JWTError, ValueError):
        raise HTTPException(status_code=400, detail="OTP token tidak valid atau sudah kadaluarsa")


def _normalize_phone(no_hp: str) -> str:
    """Normalisasi nomor ke format internasional tanpa '+': 08xxx → 628xxx"""
    n = no_hp.strip().replace("-", "").replace(" ", "")
    if n.startswith("0"):
        return "62" + n[1:]
    if n.startswith("+"):
        return n[1:]
    return n


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, db: AsyncSession = Depends(get_db)) -> Any:
    username, password = await _read_credentials(request)
    if not username or not password:
        raise HTTPException(status_code=422, detail="username & password required")

    res = await db.execute(
        text("SELECT * FROM users WHERE username = :u"),
        {"u": username},
    )
    user = res.mappings().first()
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Username atau Password Salah")

    role = str(user["role_id"]) if user["role_id"] is not None else ""
    userable_id = user.get("userable_id")
    userable_type = user.get("userable_type")

    token = create_access_token(
        sub=str(user["id"]),
        extra={
            "username": user["username"],
            "role_id": user["role_id"],
            "userable_id": userable_id,
            "userable_type": userable_type,
        },
    )

    res_role = await db.execute(
        text("""
            SELECT page_role.*, pages.*
            FROM page_role
            INNER JOIN pages ON page_role.page_id = pages.id
            WHERE role_id = :rid
        """),
        {"rid": role},
    )
    data_role = [dict(r) for r in res_role.mappings().all()]

    if role == "4":
        res_diri = await db.execute(
            text("""
                SELECT users.*,
                       roles.nama        AS info1,
                       member.kode_member AS info3,
                       member.nama        AS info2,
                       member.profile_photo,
                       member.email,
                       member.nohp,
                       member.alamat,
                       member.poin
                FROM users
                INNER JOIN roles  ON users.role_id = roles.id
                INNER JOIN member ON member.kode_member = users.userable_id
                WHERE users.userable_id = :uid
            """),
            {"uid": userable_id},
        )
        data_diri = res_diri.mappings().first()
        if not data_diri:
            raise HTTPException(status_code=404, detail="Data member tidak ditemukan")

        datas: Dict[str, Any] = {
            "token": token,
            "token_type": "bearer",
            "userid": str(user["id"]),
            "username": data_diri["username"],
            "role": data_diri["info1"],
            "profile_photo": data_diri["profile_photo"],
            "info1": data_diri["info1"],
            "info2": data_diri["info2"],
            "info3": data_diri["info3"],
            "email": data_diri["email"],
            "alamat": data_diri["alamat"],
            "nohp": data_diri["nohp"],
            "usertipe": userable_type,
            "poin": data_diri["poin"],
        }

    elif role == "1":
        datas = {
            "token": token,
            "token_type": "bearer",
            "userid": str(user["id"]),
            "username": "Admin",
            "role_id": role,
            "role": "ADMIN PUSAT",
            "pages_permission": data_role,
            "usertipe": userable_type,
        }

    else:
        res_diri = await db.execute(
            text("""
                SELECT pegawai.*,
                       outlet.*,
                       roles.nama AS role
                FROM users
                INNER JOIN pegawai ON users.userable_id = pegawai.id
                INNER JOIN outlet  ON pegawai.id_outlet = outlet.id_outlet
                INNER JOIN roles   ON users.role_id = roles.id
                WHERE pegawai.id = :uid
            """),
            {"uid": userable_id},
        )
        data_diri = res_diri.mappings().first()
        if not data_diri:
            raise HTTPException(status_code=404, detail="Data pegawai tidak ditemukan")

        datas = {
            "token": token,
            "token_type": "bearer",
            "userid": str(user["id"]),
            "username": user["username"],
            "nama": data_diri["nama"],
            "role_id": role,
            "role": data_diri["role"],
            "pages_permission": data_role,
            "outlet_id": data_diri["id_outlet"],
            "outlet_nama": data_diri["nama_outlet"],
            "usertipe": userable_type,
        }

    return {"message": datas}


# ---------------------------------------------------------------------------
# Registrasi — Step 1: validasi + kirim OTP
# ---------------------------------------------------------------------------

@router.post("/registrasi", summary="Registrasi — kirim OTP ke nomor HP")
async def registrasi(
    payload: RegistrationIn,
    db: AsyncSession = Depends(get_db),
):
    p = payload.model_dump()

    if p["kata_sandi"] != p["kata_sandi_konfirm"]:
        raise HTTPException(status_code=400, detail="Password dan Konfirmasi Password tidak sama!")

    # Cek email belum terdaftar
    r = await db.execute(
        text("SELECT 1 FROM users WHERE username = :email"),
        {"email": p["email"]},
    )
    if r.scalar() is not None:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar sebagai member")

    # Generate OTP 6 digit (cryptographically secure)
    otp = f"{secrets.randbelow(1_000_000):06d}"

    # Simpan password hash di reg_data supaya tidak perlu hash ulang saat verify
    reg_data = {
        "nama_lengkap": p["nama_lengkap"],
        "email": p["email"],
        "no_hp": p["no_hp"],
        "instagram": p["instagram"],
        "tgl_lahir": str(p["tgl_lahir"]),
        "jkel": p["jkel"],
        "pwd_hash": create_bsha256(p["kata_sandi"]),
        "alamat": p["alamat"],
        "kabupaten": p["kabupaten"],
        "kecamatan": p["kecamatan"],
        "token_fcm": p["token_fcm"],
    }

    otp_token = _make_otp_token(otp, reg_data)

    # Kirim OTP via WhatsApp
    target = _normalize_phone(p["no_hp"])
    pesan = (
        f"Kode OTP Registrasi Ayunadi CRM Anda: *{otp}*\n"
        f"Berlaku {settings.OTP_EXPIRE_MINUTES} menit. Jangan bagikan ke siapapun."
    )
    sent = await send_whatsapp(target, pesan)
    if not sent:
        raise HTTPException(status_code=502, detail="Gagal mengirim OTP, coba lagi")

    return {
        "message": f"OTP dikirim ke {p['no_hp']}",
        "otp_token": otp_token,
    }


# ---------------------------------------------------------------------------
# Registrasi — Step 2: verifikasi OTP + insert ke DB
# ---------------------------------------------------------------------------

@router.post("/verifikasi-otp", response_model=MessageOnly, summary="Verifikasi OTP registrasi")
@limiter.limit("5/minute")
async def verifikasi_otp(
    request: Request,
    payload: OtpVerifyIn,
    db: AsyncSession = Depends(get_db),
):
    token_data = _decode_otp_token(payload.otp_token)

    # Verifikasi OTP
    if _otp_hash(payload.otp_code) != token_data["otp_hash"]:
        raise HTTPException(status_code=400, detail="Kode OTP salah")

    reg = token_data["reg"]
    now = datetime.now()
    yy, mm, dd = now.strftime("%y"), now.strftime("%m"), now.strftime("%d")

    try:
        async with db.begin():
            # Cek ulang email (bisa saja didaftarkan orang lain selama OTP menunggu)
            r = await db.execute(
                text("SELECT 1 FROM users WHERE username = :email"),
                {"email": reg["email"]},
            )
            if r.scalar() is not None:
                raise HTTPException(status_code=409, detail="Email sudah terdaftar sebagai member")

            # Generate kode_member
            r = await db.execute(text("""
                SELECT kode_member FROM member
                WHERE DATE(created_at) = CURRENT_DATE
                ORDER BY RIGHT(kode_member, 4) DESC
                LIMIT 1
            """))
            last = r.scalar()
            seq = (int(last[-4:]) + 1) if last else 1
            kode_member = f"AN{yy}{mm}{dd}{seq:04d}"

            await db.execute(text("""
                INSERT INTO member (
                    kode_member, nama, jk, email, alamat,
                    kabupaten, kecamatan, nohp, instagram,
                    tgllahir, created_at, isverfi
                ) VALUES (
                    :kode_member, :nama, :jk, :email, :alamat,
                    :kabupaten, :kecamatan, :nohp, :instagram,
                    :tgllahir, NOW(), 1
                )
            """), {
                "kode_member": kode_member,
                "nama": reg["nama_lengkap"],
                "jk": reg["jkel"],
                "email": reg["email"],
                "alamat": reg["alamat"],
                "kabupaten": reg["kabupaten"],
                "kecamatan": reg["kecamatan"],
                "nohp": reg["no_hp"],
                "instagram": reg["instagram"],
                "tgllahir": reg["tgl_lahir"],
            })

            await db.execute(text("""
                INSERT INTO users (
                    username, password, role_id, userable_id,
                    created_at, token_fcm
                ) VALUES (
                    :email, :pwd, 4, :kode_member,
                    NOW(), :token_fcm
                )
            """), {
                "email": reg["email"],
                "pwd": reg["pwd_hash"],
                "kode_member": kode_member,
                "token_fcm": reg["token_fcm"],
            })

        return {"message": "Registrasi berhasil"}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Gagal menyimpan data!")
