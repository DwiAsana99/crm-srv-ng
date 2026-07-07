# API — Auth & Member

| | |
|---|---|
| **Base URL** | `https://api-crm.sbm-app.id/api/v1` |
| **Swagger UI** | `https://api-crm.sbm-app.id/docs` *(aktif saat `SHOW_DOCS=true`)* |
| **ReDoc** | `https://api-crm.sbm-app.id/redoc` *(aktif saat `SHOW_DOCS=true`)* |
| **Health check** | `https://api-crm.sbm-app.id/health` |

Semua request body: `Content-Type: application/json`
Protected endpoint wajib kirim header: `Authorization: Bearer <token>`

---

## Test Accounts

> **PENTING:** Akun ini hanya untuk development/testing. Hapus atau nonaktifkan sebelum production.

| Role | Email (username) | Password | role_id |
|---|---|---|---|
| Admin Pusat | `admin.test@sbm-app.id` | `Test1234!` | 1 |
| Member | `member.test@sbm-app.id` | `Test1234!` | 4 |

### Cara Dapat Bearer Token

**Login sebagai Admin:**
```bash
curl -s -X POST https://api-crm.sbm-app.id/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin.test@sbm-app.id","password":"Test1234!"}' \
  | python3 -m json.tool
```

**Login sebagai Member:**
```bash
curl -s -X POST https://api-crm.sbm-app.id/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"member.test@sbm-app.id","password":"Test1234!"}' \
  | python3 -m json.tool
```

Ambil `token` dari field `message.token` di response, gunakan di request selanjutnya:

```bash
# Contoh pakai token
curl -s https://api-crm.sbm-app.id/api/v1/member/ANTEST0001 \
  -H "Authorization: Bearer <token_dari_login>"
```

### Setup SQL — Jalankan Sekali di Database

```sql
-- ============================================================
-- TEST ACCOUNTS — hapus sebelum production
-- Password semua: Test1234!
-- ============================================================

-- 1. Member test (role_id = 4)
INSERT INTO member (
    kode_member, nama, jk, email, alamat,
    kabupaten, kecamatan, nohp, instagram,
    tgllahir, created_at, is_verif
) VALUES (
    'ANTEST0001', 'Member Test', 'L', 'member.test@sbm-app.id', 'Jl. Test No. 1',
    3273, 327301, '081200000001', '@member_test',
    '1995-01-01', NOW(), '1'
);

INSERT INTO users (username, password, role_id, userable_id, userable_type, created_at)
VALUES (
    'member.test@sbm-app.id',
    'bsha256$$2b$12$n6xtdybiCIlJFkw3F0QoGONN0/ZaY7lavDeCWV1NmCBYtY6iEk8CO',
    4,
    'ANTEST0001',
    'App\\Models\\Member',
    NOW()
);

-- 2. Admin test (role_id = 1)
INSERT INTO users (username, password, role_id, userable_type, created_at)
VALUES (
    'admin.test@sbm-app.id',
    'bsha256$$2b$12$n6xtdybiCIlJFkw3F0QoGONN0/ZaY7lavDeCWV1NmCBYtY6iEk8CO',
    1,
    NULL,
    NOW()
);
```

---

## 1. Registrasi

Dua langkah: submit data → verifikasi OTP via WhatsApp.

### Step 1 — Kirim OTP

```
POST /auth/registrasi
```

**Request Body**

```json
{
  "nama_lengkap": "Budi Santoso",
  "email": "budi@example.com",
  "no_hp": "081234567890",
  "instagram": "@budi",
  "tgl_lahir": "1995-06-15",
  "jkel": "L",
  "kata_sandi": "password123",
  "kata_sandi_konfirm": "password123",
  "alamat": "Jl. Merdeka No. 1",
  "kabupaten": 3273,
  "kecamatan": 327301,
  "token_fcm": "fcm_token_flutter_device"
}
```

| Field | Tipe | Keterangan |
|---|---|---|
| `nama_lengkap` | string | min 1 karakter |
| `email` | string (email) | unik, dipakai sebagai username login |
| `no_hp` | string | 6–20 digit, tujuan pengiriman OTP WA |
| `tgl_lahir` | string | format `YYYY-MM-DD` |
| `jkel` | string | `"L"` atau `"P"` |
| `kata_sandi` | string | min 8, max 512 karakter |
| `kata_sandi_konfirm` | string | harus sama dengan `kata_sandi` |
| `kabupaten` | integer | ID regency |
| `kecamatan` | integer | ID district |
| `token_fcm` | string | Firebase token perangkat Flutter |

**Response 200**

```json
{
  "message": "OTP dikirim ke 081234567890",
  "otp_token": "<jwt_string>"
}
```

> Simpan `otp_token` di Flutter. Berlaku **5 menit**.

**Response Error**

| Status | Kondisi |
|---|---|
| 400 | Password tidak sama / data tidak lengkap |
| 409 | Email sudah terdaftar |
| 502 | Gagal kirim OTP via WhatsApp |

---

### Step 2 — Verifikasi OTP

```
POST /auth/verifikasi-otp
```

**Request Body**

```json
{
  "otp_token": "<jwt_dari_step_1>",
  "otp_code": "123456"
}
```

| Field | Tipe | Keterangan |
|---|---|---|
| `otp_token` | string | JWT dari Step 1 |
| `otp_code` | string | **6 digit numerik** yang dikirim via WhatsApp (contoh: `"047823"`) |

**Response 200**

```json
{
  "message": "Registrasi berhasil"
}
```

**Response Error**

| Status | Kondisi |
|---|---|
| 400 | OTP salah / token kadaluarsa (>5 menit) |
| 409 | Email sudah terdaftar (race condition) |

---

## Alur Registrasi — Sudut Pandang Flutter

4 endpoint diakses berurutan. Semua publik (tidak perlu token).

| # | Method | Endpoint | Tujuan |
|---|---|---|---|
| 1 | GET | `/location/kabupaten` | Isi dropdown Kabupaten |
| 2 | GET | `/location/kecamatan/{kabupaten_id}` | Isi dropdown Kecamatan (setelah pilih kabupaten) |
| 3 | POST | `/auth/registrasi` | Submit form → terima `otp_token` + kirim OTP ke WA |
| 4 | POST | `/auth/verifikasi-otp` | Masukkan OTP → akun dibuat, `is_verif='1'` |

### Diagram Alur

```
[Screen Form Registrasi — initState()]
       │
       ▼
GET /location/kabupaten          ← load dropdown Kabupaten
       │
       ▼
 User pilih Kabupaten
       │
       ▼
GET /location/kecamatan/{id}     ← load dropdown Kecamatan
       │
       ▼
 User isi semua field form
       │
       ▼
POST /auth/registrasi
       │
  ┌────┴──────────────────────────────────┐
  │ 200 OK                                │ 400/409/502 → tampilkan error
  │ { message, otp_token }                │
  └────┬──────────────────────────────────┘
       │
  Simpan otp_token di state
  Navigasi ke Screen OTP
       │
       ▼
 User terima 6 digit OTP via WhatsApp
       │
       ▼
POST /auth/verifikasi-otp
  { otp_token, otp_code }
       │
  ┌────┴──────────────────────────────────┐
  │ 200 OK                                │ 400 → OTP salah/kadaluarsa
  │ member + user tersimpan di DB         │   → kembali ke form registrasi
  │ isverfi = 1                           │
  └────┬──────────────────────────────────┘
       │
  Navigasi ke halaman Login
```

---

### Endpoint 1 — GET /location/kabupaten

Publik. Dipanggil di `initState()` screen form registrasi.

**Response 200**

```json
[
  { "id": 3273, "nama": "Kota Bandung" },
  { "id": 3274, "nama": "Kota Cimahi" }
]
```

**Dart**

```dart
Future<List<Map<String, dynamic>>> loadKabupaten() async {
  final res = await http.get(Uri.parse('$baseUrl/location/kabupaten'));
  final List body = jsonDecode(res.body);
  return body.cast<Map<String, dynamic>>();
}

// Tampilkan di DropdownButton
DropdownButton<int>(
  items: _kabupatenList.map((k) => DropdownMenuItem<int>(
    value: k['id'] as int,
    child: Text(k['nama']),
  )).toList(),
  onChanged: (val) {
    setState(() => _selectedKabupaten = val);
    loadKecamatan(val!);   // trigger load kecamatan
  },
)
```

---

### Endpoint 2 — GET /location/kecamatan/{kabupaten_id}

Publik. Dipanggil saat user memilih kabupaten.

**Contoh:** `GET /location/kecamatan/3273`

**Response 200**

```json
[
  { "id": 327301, "nama": "Sukasari" },
  { "id": 327302, "nama": "Sukajadi" }
]
```

**Dart**

```dart
Future<void> loadKecamatan(int kabupatenId) async {
  final res = await http.get(
    Uri.parse('$baseUrl/location/kecamatan/$kabupatenId'),
  );
  setState(() {
    _kecamatanList = (jsonDecode(res.body) as List)
        .cast<Map<String, dynamic>>();
    _selectedKecamatan = null;   // reset pilihan sebelumnya
  });
}
```

---

### Endpoint 3 — POST /auth/registrasi

Kirim data form. Server generate OTP, kirim ke WA, kembalikan `otp_token` (JWT 5 menit).

**Dart**

```dart
String? _otpToken;   // simpan di state atau provider

Future<void> submitRegistrasi() async {
  final body = {
    "nama_lengkap": _namaCtrl.text,
    "email": _emailCtrl.text,
    "no_hp": _noHpCtrl.text,        // format 08xxx atau 628xxx
    "instagram": _igCtrl.text,
    "tgl_lahir": _tglLahir,          // "YYYY-MM-DD"
    "jkel": _jkel,                   // "L" atau "P"
    "kata_sandi": _passCtrl.text,
    "kata_sandi_konfirm": _passConfirmCtrl.text,
    "alamat": _alamatCtrl.text,
    "kabupaten": _selectedKabupaten,  // int
    "kecamatan": _selectedKecamatan,  // int
    "token_fcm": await getFcmToken(), // Firebase token perangkat
  };

  final res = await http.post(
    Uri.parse('$baseUrl/auth/registrasi'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode(body),
  );

  final resp = jsonDecode(res.body);

  if (res.statusCode == 200) {
    _otpToken = resp['otp_token'];   // JWT — simpan di state
    Navigator.pushNamed(context, '/otp-verify');
  } else {
    // resp['detail'] berisi pesan error
    showError(resp['detail']);
  }
}
```

**Error yang mungkin:**

| Status | `detail` | Tindakan Flutter |
|---|---|---|
| 400 | "Password dan Konfirmasi Password tidak sama!" | Tampilkan di form |
| 409 | "Email sudah terdaftar sebagai member" | Arahkan ke login |
| 502 | "Gagal mengirim OTP, coba lagi" | Tampilkan, coba submit ulang |

---

### Endpoint 4 — POST /auth/verifikasi-otp

Submit OTP 6 digit dari WA + `otp_token` dari Step 3. Server verifikasi, lalu INSERT ke tabel `member` dan `users` dengan `is_verif='1'`.

**Dart**

```dart
Future<void> verifikasiOtp(String otpCode) async {
  if (_otpToken == null) return;

  final res = await http.post(
    Uri.parse('$baseUrl/auth/verifikasi-otp'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'otp_token': _otpToken,
      'otp_code': otpCode,   // string 6 digit, contoh: "047823"
    }),
  );

  final resp = jsonDecode(res.body);

  if (res.statusCode == 200) {
    _otpToken = null;   // buang, tidak dipakai lagi
    Navigator.pushReplacementNamed(context, '/login');
    showSuccess('Registrasi berhasil! Silakan login.');
  } else if (res.statusCode == 400) {
    final detail = resp['detail'] as String;
    if (detail.contains('kadaluarsa')) {
      // OTP expired → kembali ke form registrasi
      Navigator.pop(context);
      showError('Kode OTP kadaluarsa. Silakan daftar ulang.');
    } else {
      // OTP salah
      showError('Kode OTP salah. Coba lagi.');
    }
  }
}
```

> OTP berlaku **5 menit**. Setelah expired, `otp_token` ditolak dengan `400`. Flutter harus arahkan user kembali ke form registrasi dan submit ulang.

---

## 2. Login

```
POST /auth/login
```

Rate limit: **10 request/menit per IP**.

**Request Body** (JSON atau form-data)

```json
{
  "username": "budi@example.com",
  "password": "password123"
}
```

**Response 200 — Role Member (role_id: 4)**

```json
{
  "message": {
    "token": "<jwt_access_token>",
    "token_type": "bearer",
    "userid": "42",
    "username": "budi@example.com",
    "role": "Member",
    "profile_photo": "upload/member/foto.jpg",
    "info1": "Member",
    "info2": "Budi Santoso",
    "info3": "AN260101001",
    "email": "budi@example.com",
    "alamat": "Jl. Merdeka No. 1",
    "nohp": "081234567890",
    "usertipe": "App\\Models\\Member",
    "poin": 1500
  }
}
```

**Response 200 — Role Admin Pusat (role_id: 1)**

```json
{
  "message": {
    "token": "<jwt_access_token>",
    "token_type": "bearer",
    "userid": "1",
    "username": "Admin",
    "role_id": "1",
    "role": "ADMIN PUSAT",
    "pages_permission": [...],
    "usertipe": null
  }
}
```

**Response 200 — Role Pegawai/Outlet (role_id: lain)**

```json
{
  "message": {
    "token": "<jwt_access_token>",
    "token_type": "bearer",
    "userid": "10",
    "username": "kasir01",
    "nama": "Siti Rahayu",
    "role_id": "2",
    "role": "Kasir",
    "pages_permission": [...],
    "outlet_id": 3,
    "outlet_nama": "Outlet Bandung",
    "usertipe": "App\\Models\\Pegawai"
  }
}
```

**Simpan token di Flutter:**

```dart
// Ambil dari response
final token = response['message']['token'];
// Simpan ke secure storage
await storage.write(key: 'token', value: token);
```

**Response Error**

| Status | Kondisi |
|---|---|
| 401 | Username atau password salah |
| 404 | Data member/pegawai tidak ditemukan di DB |
| 422 | Username atau password kosong |
| 429 | Rate limit terlampaui (>10/menit) |

---

## 3. Logout

Tidak ada server-side logout (token JWT stateless).

**Client-side logout (Flutter):**

```dart
await storage.delete(key: 'token');
// Arahkan ke halaman login
```

Token otomatis tidak valid setelah **60 menit** (sesuai `ACCESS_TOKEN_EXPIRE_MINUTES`).

---

## 4. Lihat Profil Member

```
GET /member/{kode_member}
```

Publik — tidak perlu token.

**Contoh:**

```
GET /member/AN260101001
```

**Response 200**

```json
{
  "kode_member": "AN260101001",
  "nama": "Budi Santoso",
  "jk": "L",
  "email": "budi@example.com",
  "alamat": "Jl. Merdeka No. 1",
  "kabupaten": 3273,
  "kecamatan": 327301,
  "nohp": "081234567890",
  "instagram": "@budi",
  "tgllahir": "1995-06-15",
  "profile_photo": "upload/member/foto.jpg",
  "poin": 1500
}
```

**Response Error**

| Status | Kondisi |
|---|---|
| 404 | Kode member tidak ditemukan |

---

## 5. Lihat Poin

Poin tersedia di dua tempat:

### Dari response Login

```json
{
  "message": {
    "poin": 1500,
    ...
  }
}
```

### Dari endpoint Profil

```
GET /member/{kode_member}
Authorization: Bearer <token>
```

```json
{
  "poin": 1500,
  ...
}
```

`kode_member` tersedia di field `info3` pada response login member.

---

## Catatan Flutter

### Alur Registrasi Lengkap (Diagram)

```
[Form Registrasi]
       │
       ▼
POST /auth/registrasi
       │
  ┌────┴────────────────────────────┐
  │ Sukses (200)                    │ Gagal (409 / 400 / 502)
  │ { otp_token, message }          │ Tampilkan error ke user
  └────┬────────────────────────────┘
       │
       ▼
 Simpan otp_token sementara
 Tampilkan screen input OTP
       │
       ▼
 User masukkan 6 digit dari WA
       │
       ▼
POST /auth/verifikasi-otp
  { otp_token, otp_code }
       │
  ┌────┴────────────────────────────┐
  │ Sukses (200)                    │ Gagal (400)
  │ member + user disimpan ke DB    │ OTP salah / kadaluarsa
  │ isverfi = 1 di tabel member     │ Tampilkan error, minta OTP ulang
  └────┬────────────────────────────┘
       │
       ▼
 Arahkan ke halaman Login
```

### Konfigurasi Base URL di Flutter

```dart
// constants.dart atau api_service.dart
const String baseUrl = 'https://api-crm.sbm-app.id/api/v1';
```

### Implementasi Flutter — Registrasi

```dart
// ── State yang perlu disimpan sementara ──
String? _otpToken;

// ── Step 1: Submit form registrasi ──
Future<void> submitRegistrasi(Map<String, dynamic> formData) async {
  final response = await http.post(
    Uri.parse('$baseUrl/auth/registrasi'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode(formData),
  );

  final body = jsonDecode(response.body);

  if (response.statusCode == 200) {
    _otpToken = body['otp_token'];   // simpan JWT sementara
    // Navigasi ke screen OTP
    Navigator.pushNamed(context, '/otp-verify');
  } else {
    // Tampilkan pesan error
    showError(body['detail']);       // contoh: "Email sudah terdaftar"
  }
}

// ── Step 2: Verifikasi OTP ──
Future<void> verifikasiOtp(String otpCode) async {
  if (_otpToken == null) return;

  final response = await http.post(
    Uri.parse('$baseUrl/auth/verifikasi-otp'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'otp_token': _otpToken,
      'otp_code': otpCode,          // 6 digit numerik dari WA
    }),
  );

  final body = jsonDecode(response.body);

  if (response.statusCode == 200) {
    _otpToken = null;               // buang token OTP
    // Registrasi berhasil, is_verif='1' tersimpan di tabel member
    Navigator.pushReplacementNamed(context, '/login');
    showSuccess('Registrasi berhasil! Silakan login.');
  } else if (response.statusCode == 400) {
    showError(body['detail']);      // "Kode OTP salah" / "token kadaluarsa"
  }
}
```

### Handle OTP Kadaluarsa

OTP berlaku **5 menit**. Jika user terlambat input:

```dart
// Response: 400 "OTP token tidak valid atau sudah kadaluarsa"
if (response.statusCode == 400 &&
    body['detail'].toString().contains('kadaluarsa')) {
  // Kembali ke form registrasi, minta kirim ulang
  Navigator.pop(context);
  showError('Kode OTP kadaluarsa. Silakan daftar ulang.');
}
```

### Struktur penyimpanan token

```dart
// Login berhasil
final data = response['message'];
await storage.write(key: 'token',       value: data['token']);
await storage.write(key: 'userid',      value: data['userid']);
await storage.write(key: 'kode_member', value: data['info3']);   // khusus role 4
await storage.write(key: 'role',        value: data['role']);
```

### Header untuk protected endpoint

```dart
final token = await storage.read(key: 'token');
final headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer $token',
};
```

### Handle token expired (401)

```dart
if (response.statusCode == 401) {
  // Hapus token, redirect ke login
  await storage.deleteAll();
  Navigator.pushReplacementNamed(context, '/login');
}
```
