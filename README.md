# ASTRA AI — Starter Backend (v0.1)

Prototype awal untuk hackathon: Flask API, SQLite, log sintetis, dan satu aturan deteksi deterministik. AI belum diintegrasikan pada versi ini.

## 1. Jalankan di Windows

Install Python 3.11 atau yang lebih baru dari python.org. Saat instalasi, centang **Add Python to PATH**. Buka folder `astra-ai-starter` di VS Code, lalu buka terminal PowerShell di folder tersebut.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m backend.app
```

Jika `py` tidak dikenali, coba `python --version`. Jika versi Python tampil, buat virtual environment dengan `python -m venv .venv`.

Server akan berjalan pada `http://127.0.0.1:5000`. Biarkan terminal itu terbuka.

## 2. Muat log demo sintetis

Buka PowerShell terminal kedua di folder proyek lalu jalankan:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/ingest/sample
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/dashboard
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/alerts
```

Contoh log memakai alamat IP dokumentasi dan identitas dummy, bukan data serangan nyata. Pemanggilan sample berulang tidak akan memasukkan event yang persis sama dua kali.

## 3. Endpoint yang tersedia

- `GET /` — identitas API
- `GET /api/health` — status backend
- `GET /api/dashboard` — ringkasan dashboard
- `GET /api/alerts` — daftar alert
- `GET /api/alerts/<id>` — detail alert
- `PATCH /api/alerts/<id>` — ubah status menjadi `new`, `investigating`, atau `resolved`
- `POST /api/ingest` — ingest event melalui JSON
- `POST /api/ingest/sample` — ingest dataset demo

Contoh request `POST /api/ingest`:

```json
{
  "events": [
    {
      "timestamp": "2026-10-20T10:00:00+07:00",
      "source_ip": "192.0.2.10",
      "event_type": "login_failure",
      "username": "demo-user",
      "outcome": "failure"
    }
  ]
}
```

## 4. Aturan deteksi awal

Rule `repeated_login_failure` membuat alert saat satu IP menghasilkan setidaknya 5 kejadian login gagal dalam rentang 5 menit. Ini hanya heuristik demo; ambangnya perlu diuji dan disetel, dan alert bukan bukti pasti bahwa serangan terjadi.

## 5. Jalankan test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 6. Pembagian kerja

- Backend: pertahankan bentuk respons API agar stabil, tambahkan aturan deteksi dan tes.
- Frontend: gunakan `GET /api/dashboard` serta `GET /api/alerts`; mulai dengan mock data dan sambungkan ke API setelah siap. Jika memakai VS Code Live Server, jalankan di port 5500 (port ini sudah diizinkan oleh konfigurasi CORS). Jangan buka HTML langsung lewat `file://`.
- Berikutnya: detail bukti, database/riwayat lebih lengkap, playbook respons, lalu analisis AI lokal. Deteksi inti harus tetap berjalan saat AI tidak tersedia.

## Catatan

Server hanya bind ke `127.0.0.1`, sehingga hanya bisa diakses dari komputer lokal secara default. Jangan menaruh log sensitif atau kredensial asli ke repository publik. Jangan menghubungkan prototipe awal ini ke jaringan produksi.
