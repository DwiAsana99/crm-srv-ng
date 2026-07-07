import httpx
from app.core.config import settings

_FONNTE_URL = "https://api.fonnte.com/send"


async def send_whatsapp(target: str, message: str) -> bool:
    """
    Kirim pesan WhatsApp via Fonnte.
    target: nomor WA tanpa '+', contoh '6281234567890'
    Returns True jika berhasil, False jika gagal.
    """
    headers = {"Authorization": settings.FONNTE_TOKEN}
    payload = {
        "target": target,
        "message": message,
        "countryCode": "62",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(_FONNTE_URL, headers=headers, data=payload)
            body = res.json()
            return bool(body.get("status"))
    except Exception:
        return False
