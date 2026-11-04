# InfoLomba SMP

Agregator & mesin pencari informasi lomba jenjang SMP, disalurkan lewat kanal Telegram.

Blueprint lengkap ada di [PLAN.md](PLAN.md).

## Yang sudah jalan (M1)

- Bot menerima **forward** poster/teks lomba dari siapa pun → ekstraksi via LLM (teks + vision)
- Draft masuk **review queue** admin (`✅ Post` / `✏️ Edit` / `🗑️ Tolak`)
- Publish ke kanal: **flyer resmi apa adanya** + caption + tombol `Daftar` / `Chat CP` / `Sumber`
- Dedup otomatis (normalisasi judul + penyelenggara, fuzzy match)
- Penyimpanan SQLite + FTS5 (fondasi pencarian di M4)

Belum termasuk (lihat milestone di PLAN.md): crawler situs (M2), scheduler/reminder (M3),
inline search (M4), web publik (M5).

## Situs terbit

Versi daring: **https://smpabbs.github.io/lombaabbs/** (repo `smpabbs/lombaabbs`).

Halaman ini dibangun ulang **otomatis dua kali sehari, 08.00 dan 14.00 WIB**, oleh
GitHub Actions (`.github/workflows/pages.yml`) — jadi tetap segar walaupun laptop
dalam keadaan mati. Cron GitHub memakai UTC, maka jadwalnya `0 1 * * *` dan
`0 7 * * *`. Badge `Sisa N hari` ikut dihitung ulang tiap kali situs dibangun,
dan lomba yang pendaftarannya sudah lewat ditandai **expired** lalu disembunyikan
di balik tombol *Tampilkan yang sudah tutup*.

Karena `data/` tidak ikut di-commit, CI menyemai basis datanya sendiri dari
snapshot di `app/web/seed.py`. Tidak ada kredensial Telegram/LLM yang dibutuhkan.

## Pratinjau web statis (pra-M5)

Untuk melihat isi database tanpa menjalankan bot atau menyentuh Telegram:

```bash
python -m app.web            # isi snapshot kalau perlu, lalu bangun situs
python -m app.web seed       # hanya isi snapshot
python -m app.web build      # hanya bangun situs
```

Hasilnya `site/index.html` — satu berkas mandiri (CSS + JS menempel), cukup klik dua
kali untuk dibuka di peramban. Tampilannya meniru feed media sosial: kartu per lomba,
flyer di atas, caption di bawah, tombol `Daftar` / `Chat CP` / `Sumber`, plus pencarian
teks dan filter kategori di sisi klien.

Perintah ini **sengaja tidak memanggil `app.config.get_settings()`**, jadi bisa jalan
tanpa token Telegram atau kunci LLM. Path dibaca dari env `DB_PATH` / `MEDIA_DIR`
(default `data/infolomba.db` dan `data/media`).

Isi awal (`app/web/seed.py`) adalah **snapshot manual** dari halaman publik yang dibaca
pada 2026-11-04 — bukan crawler. Setiap entri menyimpan `sumber_url` halaman asalnya,
dan kolom yang tidak ada di halaman sumber sengaja dibiarkan kosong (tidak ditebak).
Daftar kekurangannya ada di `CATATAN_KURANG` dan ikut tercetak saat `seed` dijalankan.

Kalau penyelenggara belum merilis poster resmi, kartu memakai **logo resmi** mereka dan
labelnya jujur berbunyi `Logo resmi …` (ditandai kolom `flyer_kind = "logo"`), bukan
`Flyer resmi …`. Begitu poster asli dikirim ke bot lewat `#flyer <id>`, penandanya
kembali jadi poster.

Caption di kartu web memakai blok yang **sama** dengan yang dikirim ke kanal
(`app.publish.formatter._blocks`), jadi tidak ada teks yang dikarang khusus untuk web.
Bedanya cuma pemangkasan: kanal membuang blok opsional agar muat di batas caption
Telegram (1024 karakter), sedangkan web menampilkan seluruh blok.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

copy .env.example .env          # lalu isi nilainya
```

Isi minimal di `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_ADMIN_IDS`,
`LLM_API_KEY`.

Penting: jadikan bot **admin kanal** supaya bisa posting, dan kirim `/start` ke bot dari
akun yang ID-nya kamu taruh di `TELEGRAM_ADMIN_IDS`.

## Menjalankan

```bash
python -m app
```

Bot berjalan dengan **long polling** — tidak butuh IP publik atau webhook.

## Alur pakai

1. **Forward** sebuah poster/broadcast lomba ke bot.
2. Bot ekstrak jadi draft dan mengirim pratinjau ke admin.
3. Admin tekan `✅ Post` → tampil di kanal; `✏️ Edit` → kirim koreksi; `🗑️ Tolak` → dibuang.
4. Kalau sumber tidak punya flyer, bot menandai `needs_flyer` — kirim gambar ke bot dengan
   caption `#flyer <id>` untuk memasangkannya.

Perintah: `/start`, `/help`, `/draft <id>`, `/recent [draft|published]`.

## Test

```bash
pytest
ruff check .
```
