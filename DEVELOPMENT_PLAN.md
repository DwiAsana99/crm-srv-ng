# CRM Service — Refactor Development Plan

## Overview

Migrasi dari Flask monolitik (`srv-lama`) ke FastAPI async (`src`).
Target: lebih aman, maintainable, dan production-ready.

- **Stack**: FastAPI + SQLAlchemy async + asyncmy + Pydantic v2
- **DB**: MySQL (existing schema, tidak ada migrasi DDL)
- **Auth**: access_tokens (DB) + JWT fallback
- **Python**: 3.12+

---

## Status Saat Ini

| Komponen | Status |
|---|---|
| Struktur FastAPI | ✅ Ada |
| Config / Settings | ✅ Ada |
| DB Session (async) | ✅ Ada |
| Password security (bsha256) | ✅ Ada |
| `POST /auth/login` | ✅ Ada (ada bug) |
| `POST /auth/registrasi` | ✅ Ada |
| Auth dependency (protected routes) | ❌ Belum |
| Semua endpoint lainnya | ❌ Belum |

---

## Bug & Tech Debt — Harus Fix Duluan

### Prioritas CRITICAL

- [ ] **auth.py:66,71** — `return (dict, status_code)` bukan valid FastAPI response.
  Fix: ganti dengan `raise HTTPException(...)` atau `JSONResponse(...)`
- [ ] **auth.py:188** — duplicate import `create_bsha256` (sudah di-import baris 10)
- [ ] **security.py:60** — `datetime.utcnow()` deprecated Python 3.12+.
  Fix: `datetime.now(timezone.utc)`
- [ ] **deps/auth.py** — belum ada. Semua protected route tidak bisa dibangun tanpa ini.

### Prioritas MEDIUM

- [ ] **main.py:11** — CORS `allow_origins=["*"]` di dev mode terlalu terbuka.
  Fix: gunakan list explicit, atau env var `CORS_ORIGINS`
- [ ] **.env** — `SECRET_KEY` ter-expose di plaintext. Wajib rotate sebelum production.
- [ ] **config.py** — tambah `REFRESH_TOKEN_EXPIRE_DAYS` dan `UPLOAD_DIR` ke settings

---

## Security Rules (berlaku ke semua endpoint baru)

1. **Tidak ada string concatenation di SQL** — semua pakai parameterized query `text("... :param")`
2. **Auth header standard** — `Authorization: Bearer <token>`, bukan `Www-Authenticate`
3. **File path** — wajib `os.path.abspath()` + whitelist direktori, tolak path traversal (`../`)
4. **Password** — hanya bsha256 untuk user baru; MD5/bcrypt lama di-upgrade on-login
5. **Input validation** — semua request pakai Pydantic schema, tidak ada `request.form` raw
6. **Rate limiting** — endpoint login wajib rate limit (`slowapi`)
7. **CORS** — `CORS_ORIGINS` wajib diset explicit di production

---

## Struktur Target

```
src/
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   └── security.py
    ├── db/
    │   └── session.py
    ├── deps/
    │   ├── db.py
    │   └── auth.py          ← get_current_user dependency
    ├── models/
    │   ├── user.py          ✅ ada
    │   ├── member.py
    │   ├── order.py
    │   └── item.py
    ├── schemas/
    │   ├── auth.py          ✅ ada
    │   ├── member.py
    │   ├── order.py
    │   └── item.py
    └── api/
        └── v1/
            ├── router.py    ✅ ada
            └── endpoints/
                ├── auth.py  ✅ ada (perlu fix)
                ├── user.py
                ├── member.py
                ├── location.py
                ├── item.py
                ├── order.py
                └── file.py
```

---

## Fase Pengembangan

### FASE 0 — Fix Bug & Foundation
**Target: endpoint yang sudah ada berjalan benar**

- [ ] Fix `return tuple` di `auth.py` → `HTTPException` / `JSONResponse`
- [ ] Fix `datetime.utcnow()` → `datetime.now(timezone.utc)` di `security.py`
- [ ] Hapus duplicate import di `auth.py`
- [ ] Buat `deps/auth.py` — dependency `get_current_user`
  - Cek header `Authorization: Bearer <token>`
  - Cek `access_tokens` table di DB (prioritas, kompatibel sistem lama)
  - Fallback: verify JWT
  - Return: object user + credentials (user_id, role_id, userable_id, userable_type, username)
- [ ] Update `main.py` CORS — hapus wildcard
- [ ] Update `core/config.py` — tambah `UPLOAD_DIR`, `ALLOWED_ORIGINS`

---

### FASE 1 — User & Member
**Endpoint: profil, update profil, FCM token**

- [ ] `GET  /api/v1/member/{kode_member}` — profil member (publik)
- [ ] `PUT  /api/v1/member` — update profil (protected, role=4)
- [ ] `POST /api/v1/user/tokenfcm` — update FCM token (protected)

**Files:**
- `schemas/member.py` — `MemberOut`, `MemberUpdateIn`
- `api/v1/endpoints/member.py`
- `api/v1/endpoints/user.py`

---

### FASE 2 — Location & Item
**Endpoint: kabupaten, kecamatan, item**

- [ ] `GET /api/v1/location/kabupaten` — list semua kabupaten (publik)
- [ ] `GET /api/v1/location/kecamatan/{kabupaten_id}` — list kecamatan (publik)
- [ ] `GET /api/v1/item` — semua item (publik)
- [ ] `POST /api/v1/item` — tambah item (protected, admin only)
- [ ] `GET /api/v1/item/outlet` — item per outlet dengan search (protected)
- [ ] `GET /api/v1/item/outlet/rekomendasi` — item rekomendasi per outlet (protected)

**Files:**
- `schemas/item.py` — `ItemOut`, `ItemIn`
- `api/v1/endpoints/location.py`
- `api/v1/endpoints/item.py`

**Catatan:** query `item/item-outlet` di Flask pakai string concat (SQL injection). Wajib parameterized.

---

### FASE 3 — Order
**Endpoint: buat order, update order, list order**

- [ ] `POST /api/v1/order` — buat order baru (protected, role=4 member)
- [ ] `PUT  /api/v1/order` — update order (protected)
- [ ] `GET  /api/v1/order` — list order member / semua (protected, role-aware)
- [ ] `GET  /api/v1/order/detail` — detail order (protected)

**Files:**
- `schemas/order.py` — `OrderIn`, `OrderOut`, `OrderDetailOut`, `PesananItem`
- `api/v1/endpoints/order.py`

**Catatan:**
- No-order format: `YYMMDD{outlet_2digit}{seq_4digit}` — logic same as Flask
- Query harga dari `outlet_item` pakai parameterized, bukan string concat
- Semua dalam satu DB transaction (rollback on error)

---

### FASE 4 — Order Confirmation & Comment
**Endpoint: konfirmasi, pembayaran, komentar order**

- [ ] `POST /api/v1/order/confirm/reject` — tolak order (protected)
- [ ] `POST /api/v1/order/confirm/deliver` — kirim order (protected)
- [ ] `POST /api/v1/order/confirm/confirm` — konfirmasi order + ongkir (protected)
- [ ] `POST /api/v1/order/confirm/payment` — upload bukti bayar (protected, file upload)
- [ ] `POST /api/v1/order/confirm/payment-valid` — validasi pembayaran (protected)
- [ ] `POST /api/v1/order/comment` — tambah komentar (protected)
- [ ] `GET  /api/v1/order/comment` — list komentar (protected)
- [ ] `GET  /api/v1/order/comment/aktif` — komentar order aktif member (protected)

**Files:**
- tambah schema di `schemas/order.py`
- `api/v1/endpoints/order_confirm.py`
- `api/v1/endpoints/order_comment.py`

---

### FASE 5 — File Serving
**Endpoint: serve gambar**

- [ ] `GET /api/v1/file/img?path=...` — serve image

**Rules keamanan:**
```python
UPLOAD_DIR = settings.UPLOAD_DIR  # absolute path dari .env
safe = os.path.abspath(os.path.join(UPLOAD_DIR, requested_path))
if not safe.startswith(UPLOAD_DIR):
    raise HTTPException(403)
```

**Files:**
- `api/v1/endpoints/file.py`

---

### FASE 6 — Hardening & Production-Ready

- [ ] Tambah `slowapi` rate limiter ke `/auth/login` (max 10 req/menit per IP)
- [ ] Tambah logging middleware (request ID, duration, status)
- [ ] Tambah health check endpoint `GET /health`
- [ ] Review semua `except Exception` — jangan suppress error yang meaningful
- [ ] Set `ENV=prod` → disable `/docs` dan `/redoc`
- [ ] Rotate `SECRET_KEY` di `.env`
- [ ] Set `CORS_ORIGINS` explicit (bukan wildcard)
- [ ] Tambah `UPLOAD_DIR` ke `.env`

---

## Token System (Kompatibilitas)

Sistem lama pakai `access_tokens` table di DB (token opaque 64-char hex, 30 hari).
Sistem baru tetap support ini untuk backward compatibility dengan client lama.

### Flow `get_current_user`:

```
Authorization: Bearer <token>
        │
        ├─ cek access_tokens table
        │       ├─ found + not expired + not revoked → perpanjang expires_at → return user
        │       └─ not found → cek JWT
        │
        └─ cek JWT (python-jose)
                ├─ valid → return user
                └─ invalid → 401 Unauthorized
```

### Catatan penting:
- Token lama (dari srv-lama) tetap valid selama ada di `access_tokens`
- Client baru bisa pakai JWT atau token DB, keduanya didukung
- `_issue_legacy_token` di auth.py sudah handle ini

---

## Dependencies Tambahan yang Dibutuhkan

```txt
slowapi>=0.1.9       # rate limiting
python-multipart     # untuk file upload (UploadFile)
aiofiles             # async file write
```

---

## Urutan Pengerjaan

```
FASE 0 → FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6
  ↑
Harus selesai dulu sebelum fase lain
```

Estimasi per fase:
- Fase 0: ~1-2 jam
- Fase 1-2: ~2-3 jam
- Fase 3-4: ~3-4 jam (kompleks, banyak edge case)
- Fase 5: ~30 menit
- Fase 6: ~1-2 jam

---

## Catatan DB Schema (dari kode lama)

Tabel yang dipakai (tidak ada perubahan DDL):

| Tabel | Dipakai di |
|---|---|
| `users` | auth, semua protected route |
| `access_tokens` | auth middleware |
| `member` | registrasi, profil, order |
| `pegawai` | login (role bukan 1 dan bukan 4) |
| `outlet` | login, order |
| `roles` | login |
| `pages` | login (permissions) |
| `page_role` | login (permissions) |
| `item` | item endpoints |
| `outlet_item` | item outlet, harga order |
| `order` | order endpoints |
| `order_detail` | order endpoints |
| `order_correspondent` | comment/konfirmasi order |
| `regencies` | kabupaten |
| `districts` | kecamatan |
| `tbHistoryPoin` | riwayat transaksi (belum diport, low priority) |
