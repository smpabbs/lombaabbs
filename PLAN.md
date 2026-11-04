# InfoLomba SMP — Blueprint

Mesin pencari + agregator informasi lomba jenjang SMP, dengan **kanal Telegram** sebagai
santapan distribusi utama.

Prinsip kunci: **kanal Telegram = surface distribusi, DB = mesin pencari, bot = jembatan
keduanya.**

---

## 1. Output final tiap postingan

**Media:** foto = **flyer resmi penyelenggara, apa adanya** — tanpa edit, watermark, atau
tambahan. Sistem tidak pernah membuat gambar sendiri.

**Caption** (batas Telegram untuk foto = **1024 karakter**):

```
🎓 JUDUL LOMBA
🏫 Penyelenggara · 📚 Bidang
👥 Jenjang: SMP (Kelas 7–9) · 💰 Gratis / Rp xx
🏆 Hadiah: ...
📅 Pelaksanaan: ...
⏰ Deadline: 12 Nov 2026 (H-10)
📍 Online / Kota
📞 CP: Nama — 08xx
🔗 Daftar: <link>
📄 Sumber: <link>
```

**Inline buttons:** `🔗 Daftar` · `📞 Chat CP` (auto ubah `08xx` → `wa.me/628xx`) · `📄 Sumber`

Kalau detail melebihi 1024 char → caption versi ringkas + tombol `📖 Detail`.

---

## 2. Prinsip akuisisi flyer (penting)

| Sumber | Cara dapat flyer asli |
|---|---|
| Forward ke bot | gambar forward → pakai `file_id` langsung (tanpa re-encode) |
| Situs agregator | scrape `<meta property="og:image">`, fallback gambar utama artikel |
| Situs resmi/kampus | `og:image`; kalau poster berbentuk PDF → render halaman 1 |
| IG/TikTok (Fase 2) | unduh media post asli |
| **Tidak ada gambar** | **jangan buat sendiri** → post teks saja atau tandai `needs_flyer` |

Catatan: `sendPhoto` dengan URL mentah sering gagal kalau situs blokir hotlink → **unduh
dulu, baru upload**.

---

## 3. Pipeline

```
SUMBER → INGEST → EKSTRAK → DEDUP → DB+INDEX → REVIEW → PUBLISH (kanal) / CARI (bot)
```

---

## 4. Langkah lengkap (0 → produksi)

### Langkah 0 — Prasyarat
Akun & kunci: BotFather (bot token), channel ID, kunci LLM (Gemini Flash / OpenAI), daftar
URL sumber. Simpan di `.env`, jangan di kode.

### Langkah 1 — Bot & kanal
Bot jadi **admin kanal** (hak post + pin). Aktifkan **Topics** per kategori. Bot mode
**polling** saat dev (tak perlu IP publik).

### Langkah 2 — Skema data + penyimpanan media
Tabel `lomba` + `lomba_fts` (FTS5). Kolom CP: `cp_nama`, `cp_kontak`, `cp_wa`. Kolom flyer:
`flyer_file_id`, `flyer_url`, `flyer_local_path`, `needs_flyer`. Media disimpan
di `data/media/` sebagai backup.

### Langkah 3 — Jalur masuk A: forward-to-bot (crowdsource) ⭐
Siapa pun forward poster → bot. Gambar forward sudah flyer resmi → simpan `file_id`.
Admin bisa kirim flyer manual dengan caption `#flyer <id>` untuk melengkapi draft
`needs_flyer`.

### Langkah 4 — Jalur masuk B: crawler situs
`feedparser` (RSS), `httpx`+`selectolax` (HTML), `playwright` (JS-heavy). Prioritas:
3–6 situs agregator lalu situs resmi/kampus. Hormati `robots.txt` + rate limit.

### Langkah 5 — Ambil flyer resmi
Lihat §2. Fallback wajib: jangan mengarang gambar.

### Langkah 6 — Ekstraksi (LLM)
Teks → LLM structured output (skema Pydantic) → JSON. Poster → **vision LLM**. Ambil CP dan
deadline; normalisasi deadline ke ISO date.

### Langkah 7 — Dedup & normalisasi
Normalisasi judul + penyelenggara → `dedup_key`. Cocokkan eksak, lalu fuzzy
(`difflib.SequenceMatcher`, ambang 0.87). Nomor CP → `628xx`.

### Langkah 8 — Review queue admin
Bot kirim draft ke admin: pratinjau flyer + caption + tombol `✅ Post` / `✏️ Edit` /
`🗑️ Tolak`. Jangan auto-post di awal.

### Langkah 9 — Publish ke kanal
`sendPhoto` + caption + inline buttons, ke topic sesuai kategori.

### Langkah 10 — Penjadwalan (APScheduler)
Cron crawler (6 jam) · digest mingguan · **reminder H-3 deadline** · tandai kedaluwarsa.

### Langkah 11 — Pencarian
Inline mode `@botmu matematika gratis SMP` → FTS5. Plus menu bot dengan filter via callback.

### Langkah 12 — Web publik (opsional, SEO)
Astro/Next baca DB → halaman per lomba + metadata.

### Langkah 13 — Deploy & operasional
Docker Compose di VPS 1–2 GB. Backup DB + `data/media` harian. Log + alert crawler gagal.

### Langkah 14 — Legal & kualitas
Atribusi + link sumber asli. Jangan re-upload flyer seolah milik sendiri. Hormati
`robots.txt` & rate limit. Scraping IG/TikTok = risiko ToS/ban → **tunda**.

---

## 5. Milestone

| Milestone | Isi | Hasil |
|---|---|---|
| **M1** | Langkah 0–3, 6, 8, 9 — bot forward-to-bot, ekstraksi LLM, review, publish | Kanal terisi dari forward — bisa pakai hari ini |
| M2 | Langkah 4, 5, 7 — crawler situs + dedup | Ingest otomatis dari web |
| M3 | Langkah 10 — scheduler | Reminder H-3 + digest mingguan |
| M4 | Langkah 11 — inline search | Pencarian di Telegram |
| M5 | Langkah 12, 13 — web publik + deploy produksi | SEO + operasional stabil |

---

## 6. Struktur repo

```
infolomba/
  app/
    bot/          # handler: forward, review queue
    store/        # db.py (SQLite+FTS5), dedup.py
    extract/      # schema.py (Pydantic), llm.py (teks + vision)
    media/        # storage.py
    publish/      # formatter.py, service.py
    config.py
    textutil.py
  data/           # infolomba.db, media/
  tests/
  .env.example
  docker-compose.yml
  pyproject.toml
```

## 7. Skema database

```sql
CREATE TABLE lomba (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  judul TEXT NOT NULL, penyelenggara TEXT,
  kategori TEXT, bidang TEXT,
  jenjang TEXT DEFAULT 'SMP', kelas TEXT,
  biaya INTEGER, hadiah TEXT,
  tgl_lomba TEXT, deadline TEXT, lokasi TEXT,
  link_daftar TEXT,
  cp_nama TEXT, cp_kontak TEXT, cp_wa TEXT,
  sumber_url TEXT,
  flyer_file_id TEXT, flyer_url TEXT, flyer_local_path TEXT,
  needs_flyer INTEGER DEFAULT 0,
  status TEXT DEFAULT 'draft',
  dedup_key TEXT,
  channel_message_id INTEGER,
  created_at TEXT, updated_at TEXT
);
CREATE VIRTUAL TABLE lomba_fts USING fts5(
  judul, penyelenggara, bidang, hadiah, lokasi,
  content='lomba', content_rowid='id');
```

## 8. Infrastruktur

| Fase | Rekomendasi |
|---|---|
| Dev / M1 | Jalankan di komputer sendiri, bot mode **polling** (tanpa IP publik) |
| Produksi M2+ | VPS 1 vCPU / 1–2 GB + Docker Compose (Hetzner CX22 atau IDCloudHost lokal) |
| DB produksi | Neon / Supabase free tier (Postgres) saat migrasi dari SQLite |
| LLM | Gemini Flash (ada free tier) atau GPT-4o-mini |
