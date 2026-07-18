# Buku Kas Telegram Bot

Bot Telegram pembukuan pribadi berbahasa Indonesia untuk user yang diizinkan. Mendukung input transaksi langsung, ringkasan, pencarian, export PDF/Excel, SQLite, Docker, GitHub Codespaces, dan allowlist user ID.

> **Keamanan:** token bot yang pernah dibagikan di chat harus dianggap bocor. Revoke/regenerate token melalui `@BotFather`, lalu isi token baru hanya di `.env`. Jangan commit `.env`.

## Fitur saat ini

- Allowlist Telegram user ID; pengguna lain mendapat `Akses ditolak.`
- Data terisolasi per user.
- Input cepat:
  - `25k makan siang`
  - `kemarin 30rb bensin`
  - `+1,5jt freelance`
  - `-50.000 listrik`
  - `12/08 75k transport #kantor`
- Kategori otomatis berbasis kata kunci.
- Ringkasan hari ini, minggu ini, dan bulan ini.
- Rekap kategori, arus kas, transaksi terbesar, serta anggaran yang melewati 80%.
- Daftar transaksi terbaru dan pencarian.
- Soft-delete melalui tombol inline dengan konfirmasi.
- Edit transaksi melalui tombol inline.
- Konfirmasi untuk input ambigu.
- Kategori custom melalui `/kategori tambah Nama Kategori`.
- Anggaran melalui `/anggaran set Nama Kategori 1000000`.
- Laporan periode custom melalui `/periode DD/MM/YYYY DD/MM/YYYY`.
- Pengaturan timezone dan mata uang per user.
- Backup transaksi pribadi melalui `/backup`.
- Rate limiting per user.
- Export PDF A4 dengan ringkasan, kategori, dan daftar transaksi.
- Export Excel dengan sheet `Ringkasan`, `Transaksi`, `Kategori`, `Anggaran`, dan `Tren Harian`; transaksi berisi sumber dan waktu update.
- Audit log dasar, termasuk export.
- Cleanup otomatis file export lama sesuai `EXPORT_TTL_SECONDS`.
- Alembic migrations.
- Docker image non-root, migration entrypoint, healthcheck, dan Docker Compose dengan volume persisten.

## Status implementasi

Jalur inti yang bisa dipakai sudah tersedia: transaksi, laporan harian/mingguan/bulanan/custom, akses, database, kategori, anggaran, backup per-user, PDF, dan Excel. Fitur yang masih disiapkan sebagai tahap berikutnya sengaja tidak diklaim aktif: transaksi berulang, reminder, import Excel/CSV, restore backup melalui Telegram, tujuan tabungan, dan modul utang/piutang.

## Persyaratan

- Python 3.11+ untuk instalasi lokal; Docker image menggunakan Python 3.12.
- Token bot Telegram baru dari `@BotFather`.
- Docker Desktop hanya diperlukan untuk deployment Docker.

## Instalasi lokal Windows / Git Bash

```bash
cd /c/Users/ASUS/telegram-bookkeeping-bot
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
cp .env.example .env
```

Edit `.env` dan masukkan token baru:

```dotenv
TELEGRAM_BOT_TOKEN=TOKEN_BARU_DARI_BOTFATHER
ALLOWED_USER_IDS=123456789,987654321
ADMIN_USER_ID=123456789
DATABASE_URL=sqlite+aiosqlite:///./data/bookkeeping.db
APP_TIMEZONE=Asia/Makassar
```

Jalankan migrasi atau biarkan aplikasi membuat tabel otomatis:

```bash
alembic upgrade head
python -m app.main
```

Alternatif entry point:

```bash
bookkeeping-bot
```

Jangan menjalankan dua proses polling untuk bot yang sama pada waktu bersamaan.

## Docker

Pastikan Docker Desktop aktif, lalu:

```bash
cp .env.example .env
# Edit .env dan masukkan token baru

docker compose up -d --build
docker compose logs -f bookkeeping-bot
```

Data tersimpan pada volume Docker `bookkeeping-data`, export pada `bookkeeping-exports`, dan backup pada `bookkeeping-backups`. Untuk menghentikan:

```bash
docker compose down
```

`docker compose down -v` akan menghapus volume data; jangan jalankan kecuali memang ingin menghapus database.

## GitHub Codespaces

Repository ini sudah memiliki `.devcontainer/devcontainer.json`, sehingga Codespace dapat dibuat langsung dari branch `main`.

### 1. Buat Codespace

1. Buka [repository pembukuan](https://github.com/AryaNyoman/pembukuan).
2. Klik **Code** → **Codespaces** → **Create codespace on main**.
3. Tunggu proses pembuatan container selesai. `postCreateCommand` akan memasang dependency dan menjalankan migrasi.

### 2. Tambahkan secret Telegram

Token lama yang pernah dibagikan tidak boleh digunakan. Buat/regenerate token baru melalui `@BotFather`, lalu di GitHub buka:

**Profile → Settings → Codespaces → Secrets → New secret**

Buat secret:

```text
Name: TELEGRAM_BOT_TOKEN
Value: token baru dari BotFather
Repository access: AryaNyoman/pembukuan
```

Jangan menaruh token di `.env`, source code, README, atau commit GitHub. Secret Codespaces akan tersedia sebagai environment variable setelah Codespace dibuat/restart.

### 3. Jalankan bot di Codespace

Di terminal Codespace:

```bash
# ALLOWED_USER_IDS dan ADMIN_USER_ID diambil dari Codespaces Secrets.
./scripts/codespace-start.sh
```

Script tersebut menjalankan `alembic upgrade head`, kemudian `python -m app.main`. Bot menggunakan long polling, jadi tidak membutuhkan port publik atau port forwarding.

Untuk menjalankan di background selama Codespace tetap aktif:

```bash
nohup ./scripts/codespace-start.sh > /tmp/bookkeeping-bot.log 2>&1 &
```

Cek log tanpa mencetak token:

```bash
tail -f /tmp/bookkeeping-bot.log
```

Hentikan bot:

```bash
./scripts/codespace-stop.sh
```

### 4. Batasan Codespaces

- Laptop boleh dimatikan setelah bot benar-benar berjalan di Codespace.
- Jika Codespace dihentikan, proses bot ikut berhenti.
- Codespace default dapat timeout setelah sekitar 30 menit tanpa aktivitas; pengaturan timeout dapat diubah di preferensi akun, tetapi tetap bukan jaminan uptime 24/7.
- Codespace yang aktif menggunakan compute dan dapat menimbulkan biaya setelah kuota gratis habis. Codespace yang berhenti tetap dapat menimbulkan biaya storage.
- Untuk layanan pembukuan 24/7 yang lebih stabil, gunakan VPS atau host always-on.

## Perintah Telegram

- `/start` — onboarding dan contoh input.
- `/help` — bantuan.
- `/hariini` — laporan hari ini.
- `/minggu` — laporan minggu berjalan.
- `/bulan` — laporan bulan berjalan.
- `/terakhir` — sepuluh transaksi terbaru.
- `/cari kata` — pencarian deskripsi/tag.
- `/export` — tombol export PDF/Excel.
- `/anggaran` — melihat anggaran yang tersedia.
- `/pengaturan` — melihat timezone dan mata uang.
- `/batal` — membatalkan operasi.

## Format transaksi

Tanpa prefix, transaksi dianggap pengeluaran. Gunakan `+`, `masuk`, atau `pemasukan` untuk pemasukan. Gunakan `-`, `keluar`, atau `pengeluaran` untuk pengeluaran.

```text
25k makan siang
25rb makan siang
150000 belanja bulanan
1,5jt pemasukan freelance
+5000000 gaji
kemarin 45k bensin
12/08 75k transport
30k kopi #kantor
```

Nominal uang disimpan sebagai integer rupiah, bukan float.

## Test dan lint

```bash
pytest -q
ruff check .
ruff format --check .
python -c "import app; print(app.__version__)"
```

Test export membutuhkan `pypdf` yang dipasang melalui extra `dev`.

## Backup SQLite

Backup aman SQLite dapat dibuat dari Python:

```bash
python -c "from app.services.backup import create_sqlite_backup; print(create_sqlite_backup('sqlite+aiosqlite:///./data/bookkeeping.db', './backups'))"
```

Simpan backup di lokasi berbeda secara berkala. Untuk produksi, gunakan disk/server dengan backup terenkripsi dan uji restore secara berkala.

## Keamanan operasional

- Jangan masukkan token ke source, README, screenshot, Git, atau log.
- Token lama yang pernah terekspos harus dicabut.
- Jangan membuka port database ke internet.
- Pastikan `.env` memiliki permission yang wajar.
- Backup berisi data keuangan; simpan secara terenkripsi dan batasi akses.
- Allowlist adalah pembatas akses bot, bukan pengganti keamanan akun Telegram atau keamanan server.
- Hosting VPS, storage, dan transfer data bisa menimbulkan biaya; tidak ada jaminan hosting gratis selamanya.

## Struktur

```text
app/
  config.py                 konfigurasi `.env`
  main.py                   entry point polling
  security.py               allowlist dan sanitasi nama file
  handlers/                 middleware dan handler Telegram
  keyboards/                inline keyboard
  db/                       SQLAlchemy models/session/repository
  services/                 parser, report, PDF/Excel, backup, scheduler
alembic/                    migrasi database
 tests/                     test parser/security/report/export
Dockerfile
docker-compose.yml
```

## Troubleshooting

- **`TELEGRAM_BOT_TOKEN is missing`**: isi token baru di `.env`.
- **Bot tidak merespons**: pastikan hanya ada satu proses polling dan cek `docker compose logs`.
- **Akses ditolak**: cek Telegram numeric user ID di `ALLOWED_USER_IDS`.
- **Database error**: pastikan folder `data/` ada dan jalankan `alembic upgrade head`.
- **PDF/Excel gagal**: jalankan `pip install -e '.[dev]'`, lalu ulangi test export.
- **Token muncul di log**: hentikan proses, cabut token di BotFather, cari dan hapus secret dari log/riwayat, lalu gunakan token baru.

## Lisensi

Tambahkan lisensi proyek sesuai kebutuhan deployment Anda. Dependensi pihak ketiga tetap mengikuti lisensinya masing-masing.

## Roadmap

- Wizard anggaran/category custom.
- Transaksi berulang dengan konfirmasi.
- Reminder harian.
- Import CSV/XLSX dengan preview.
- Backup/restore melalui Telegram dengan validasi dan enkripsi.
- Tujuan tabungan serta modul utang/piutang terpisah.
- PostgreSQL deployment dan observability produksi.

Fitur roadmap tidak boleh dianggap aktif sebelum ada implementasi dan test yang lulus.
