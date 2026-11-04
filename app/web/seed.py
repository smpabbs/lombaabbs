"""Isi awal database dari hasil pencarian web manual.

Ini **bukan crawler** — ini snapshot manual dari halaman publik yang dibaca pada
2026-11-04, dipakai supaya situs statis punya isi nyata untuk dilihat. Setiap
entri menyimpan `sumber_url` halaman asalnya agar bisa diperiksa ulang.

Kolom yang tidak tercantum di halaman sumber sengaja dibiarkan kosong, bukan
ditebak. Lihat `CATATAN_KURANG` untuk daftar yang belum lengkap.
"""

from __future__ import annotations

from typing import Any

from app.store.db import Database
from app.store.dedup import dedup_key

SNAPSHOT_DATE = "2026-11-04"

#: Ringkasan apa yang belum lengkap dari tiap entri, untuk ditampilkan ke admin.
CATATAN_KURANG: dict[str, str] = {
    "JSTO Champions 2026": "tanpa nomor CP di halaman sumber",
    "Pratibha Olimpiade Sains Nasional 3.1": "nomor CP hanya nomor admin, bukan narahubung bernama",
    "Kompetisi Sains Siswa Muslim Indonesia (KoSSMI) 2026": (
        "biaya dan jadwal pelaksanaan tidak dicantumkan di halaman sumber"
    ),
    "Olimpiade Sains Indonesia (OSI) 2026": "biaya tertulis 'GRATIS' sekaligus 'Rp 50.000'",
    "Kompetisi Sains Madrasah (KSM) Tahun 2026": "biaya tertulis 'GRATIS' sekaligus 'Rp 50.000'",
    "Junior Science Olympiad (JSO) 2027 Jawa Timur": (
        "tidak ada CP dan daftar bidang di halaman sumber"
    ),
    "Olimpiade Sains Madrasah (OSM) Banten 2026": "pendaftaran sudah ditutup 31 Okt 2026",
    "Olimpiade Sains Nasional (OSN) SMP 2026": (
        "tanggal pasti per tahap belum tersedia; flyer diambil dari citra resmi event OSN di "
        "portal Puspresnas (gambar di artikel sekolah ternyata buatan AI, jadi tidak dipakai)"
    ),
    "OU Festival 12 (Olimpiade Update Festival) 2026/2027": (
        "tak ada CP/telepon di halaman sumber (kontak hanya lewat DM IG @ou_festival); "
        "biaya berbeda per cabang; poster resmi belum dirilis, jadi gambar kartu memakai "
        "logo resmi festival"
    ),
    "6th Superstar Science Olympiad 2026/2027": (
        "besaran hadiah tidak dicantumkan; penyelenggara hanya memublikasikan logo dan foto "
        "kegiatan sehingga gambar kartu memakai logo resmi (poster resmi belum ditemukan); "
        "biaya naik tiap gelombang"
    ),
    "ASCIENCO 12 (South East Asia Student Science Street Olympiad) 2027": (
        "tak ada CP sama sekali; besaran hadiah belum jelas"
    ),
}

SEED: tuple[dict[str, Any], ...] = (
    {
        "judul": "JSTO Champions 2026",
        "penyelenggara": "SMA Unggulan Rushd × Algobash.com",
        "kategori": "akademik",
        "bidang": "Matematika, Sains (IPA), Informatika",
        "kelas": "7-9",
        "biaya": 0,
        "hadiah": (
            "Per bidang: emas Rp 1.000.000 + beasiswa SMA Unggulan Rushd (3 pemenang), "
            "perak Rp 500.000 (5), perunggu Rp 350.000 (7), medali, sertifikat nasional, "
            "merchandise"
        ),
        "ringkasan": (
            "Kompetisi nasional tiga tahap untuk SMP/MTs/sederajat kelas 7-9 se-Indonesia. "
            "Kualifikasi regional dan seleksi nasional dilaksanakan daring, grand final luring "
            "di SMA Unggulan Rushd."
        ),
        "tgl_lomba": (
            "14-15 Nov 2026 (kualifikasi), 28-29 Nov 2026 (nasional), "
            "18-20 Des 2026 (grand final)"
        ),
        "deadline": "2026-10-30",
        "lokasi": "Daring (grand final: luring di SMA Unggulan Rushd)",
        "link_daftar": "https://jsto.id/peserta",
        "flyer_url": "https://jsto.id/champion.png",
        "sumber_url": "https://jsto.id/champions",
    },
    {
        "judul": "Pratibha Olimpiade Sains Nasional 3.1",
        "penyelenggara": "PT. Kompetisi Online Prestasi Nusantara",
        "kategori": "akademik",
        "bidang": "Matematika, Bahasa Inggris, Biologi, Fisika, Sejarah",
        "kelas": "7-9",
        "biaya": 0,
        "hadiah": (
            "Medali & trophy, e-sertifikat & e-piagam nasional, seleksi beasiswa untuk finalis, "
            "uang pendidikan, souvenir, apresiasi guru pembimbing"
        ),
        "ringkasan": (
            "Kompetisi daring nasional jenjang SMP/MTs kelas 7-9. Tahap penyisihan 22 November "
            "2026 dan final 6 Desember 2026, dikerjakan lewat CBT."
        ),
        "tgl_lomba": "22 November 2026 (penyisihan), 6 Desember 2026 (final)",
        "deadline": "2026-11-19",
        "lokasi": "Daring (CBT)",
        "link_daftar": (
            "https://pendaftaran.kompetisiku.my.id/peserta/index.php"
            "?page=pendaftaran_individu&invite=65-3616a9d7"
        ),
        "cp_nama": "Admin POSION 3.1",
        "cp_kontak": "0851-8597-2404",
        "flyer_url": (
            "https://kompetisi.in/Assets/uploads/poster/poster_1788929085_fbd214.webp"
        ),
        "sumber_url": (
            "https://kompetisi.in/kompetisi/pratibha-olimpiade-sains-nasional-3-1-bffae0"
        ),
    },
    {
        "judul": "Kompetisi Sains Siswa Muslim Indonesia (KoSSMI) 2026",
        "penyelenggara": "KOSSMI",
        "kategori": "akademik",
        "bidang": "Matematika, IPA, IPS (Level 3 – Jabir Ibnu Hayyan)",
        "kelas": "7-9",
        "ringkasan": (
            "Pendaftaran jenjang SMP/MTs kelas 7-9 untuk Level 3 (Jabir Ibnu Hayyan) pada bidang "
            "Matematika, IPA, dan IPS. Biaya dan jadwal pelaksanaan belum dicantumkan di halaman "
            "pendaftaran."
        ),
        "link_daftar": (
            "https://docs.google.com/forms/d/e/1FAIpQLSekLbB3mIKbYTn-rCmjgHV_oMpjB7NGedEwMzTvqR"
            "-jDrs_Mw/viewform"
        ),
        "cp_nama": "Ka Widya",
        "cp_kontak": "085218870880",
        "flyer_url": "https://kossmi.com/wp-content/uploads/2026/01/6.jpg",
        "sumber_url": "https://kossmi.com/pendaftaran-kossmi-2026/",
    },
    {
        "judul": "Olimpiade Sains Indonesia (OSI) 2026",
        "penyelenggara": "POSI (Pusat Olimpiade Sains Indonesia)",
        "kategori": "akademik",
        "bidang": "56 bidang (termasuk jenjang SMP)",
        "kelas": "7-9",
        "ringkasan": (
            "Olimpiade daring POSI dengan 56 bidang, terbuka untuk SD, SMP, SMA, dan mahasiswa. "
            "Halaman sumber mencantumkan biaya 'GRATIS' sekaligus 'Rp 50.000' — perlu "
            "dicek di juknis."
        ),
        "tgl_lomba": "22 November 2026",
        "deadline": "2026-11-20",
        "lokasi": "Daring",
        "link_daftar": "https://posi.id/competitions/olimpiade-sains-indonesia-osi-2026",
        "flyer_url": "https://posi.id/storage/competition/1792381638-banner-niz3wtp805h.png",
        "sumber_url": "https://posi.id/competitions/olimpiade-sains-indonesia-osi-2026",
    },
    {
        "judul": "Kompetisi Sains Madrasah (KSM) Tahun 2026",
        "penyelenggara": "POSI (Pusat Olimpiade Sains Indonesia)",
        "kategori": "akademik",
        "bidang": "43 bidang (termasuk jenjang SMP)",
        "kelas": "7-9",
        "ringkasan": (
            "Kompetisi daring dengan 43 bidang untuk SD, SMP, SMA, dan mahasiswa. Halaman sumber "
            "mencantumkan biaya 'GRATIS' sekaligus 'Rp 50.000' — perlu dicek di juknis."
        ),
        "tgl_lomba": "20 Desember 2026",
        "deadline": "2026-12-18",
        "lokasi": "Daring",
        "link_daftar": "https://posi.id/competitions/kompetisi-sains-madrasah-ksm-tahun-2026",
        "flyer_url": "https://posi.id/storage/competition/1793091184-banner-rvpytl6b0zq.png",
        "sumber_url": "https://posi.id/competitions/kompetisi-sains-madrasah-ksm-tahun-2026",
    },
    {
        "judul": "Junior Science Olympiad (JSO) 2027 Jawa Timur",
        "penyelenggara": "POSI (Pusat Olimpiade Sains Indonesia)",
        "kategori": "akademik",
        "bidang": "13 bidang",
        "kelas": "7-9",
        "biaya": 100_000,
        "ringkasan": (
            "Olimpiade luring tingkat Provinsi Jawa Timur untuk jenjang TK, SD, dan SMP. "
            "Pendaftaran dibuka 1 Desember 2026. Tidak ada nomor CP di halaman sumber."
        ),
        "tgl_lomba": "10 April 2027",
        "deadline": "2027-03-21",
        "lokasi": "Luring (Jawa Timur)",
        "link_daftar": "https://posi.id/competitions/junior-science-olympiad-jso-tahun-2027-provinsi-jawa-timur",
        "flyer_url": "https://posi.id/storage/competition/1793180738-banner-pqzujvcqed.jpeg",
        "sumber_url": "https://posi.id/competitions/junior-science-olympiad-jso-tahun-2027-provinsi-jawa-timur",
    },
    {
        "judul": "Olimpiade Sains Madrasah (OSM) Banten 2026",
        "penyelenggara": "POSI (Pusat Olimpiade Sains Indonesia)",
        "kategori": "akademik",
        "bidang": "11 bidang",
        "kelas": "7-9",
        "biaya": 100_000,
        "ringkasan": (
            "Olimpiade luring tingkat Provinsi Banten untuk jenjang SD, SMP, dan SMA. "
            "Pendaftaran sudah ditutup 31 Oktober 2026; dicantumkan sebagai arsip."
        ),
        "tgl_lomba": "14 November 2026",
        "deadline": "2026-10-31",
        "lokasi": "Luring (Banten)",
        "link_daftar": (
            "https://posi.id/competitions/olimpiade-sains-madrasah-osm-provinsi-banten-tahun-2026"
        ),
        "flyer_url": "https://posi.id/storage/competition/1789440125-banner-cino1miyb2r.png",
        "sumber_url": (
            "https://posi.id/competitions/olimpiade-sains-madrasah-osm-provinsi-banten-tahun-2026"
        ),
    },
    {
        "judul": "Olimpiade Sains Nasional (OSN) SMP 2026",
        "penyelenggara": "Pusat Prestasi Nasional (Puspresnas), Kemendikdasmen",
        "kategori": "akademik",
        "bidang": "Matematika, IPA, IPS",
        "kelas": "7-8",
        "biaya": 0,
        "ringkasan": (
            "Ajang resmi Puspresnas. Peserta adalah siswa kelas VII atau VIII tahun ajaran "
            "2025/2026, diseleksi berjenjang mulai dari tingkat sekolah (OSN-S). Cabang lomba: "
            "Matematika, IPA, dan IPS."
        ),
        "tgl_lomba": "Februari – Agustus 2026",
        "lokasi": "Berjenjang (sekolah → kabupaten/kota → provinsi → nasional)",
        "link_daftar": "https://pusatprestasinasional.kemendikdasmen.go.id/jenjang/smp",
        "flyer_url": (
            "https://pusatprestasinasional.kemendikdasmen.go.id/uploads/event/"
            "FQSGTT7HP8SXUrWME31rg97fDdFziiprtI8ZzIiV.png"
        ),
        "sumber_url": (
            "https://www.smpnegeri1bangli.sch.id/2026/02/12/"
            "resmi-dirilis-pedoman-dan-jadwal-pelaksanaan-olimpiade-sains-nasional-osn-"
            "jenjang-smp-tahun-2026/"
        ),
    },
    {
        "judul": "OU Festival 12 (Olimpiade Update Festival) 2026/2027",
        "penyelenggara": "Olimpiade Update (OU Festival)",
        "kategori": "akademik",
        "bidang": (
            "OPSILON (Matematika, IPA, IPS, B. Indonesia, B. Inggris), "
            "KOSA KATA (puisi & cerpen), KOMPAS (poster digital)"
        ),
        "kelas": "7-9",
        "biaya": 30_000,
        "ringkasan": (
            "Festival enam lomba tingkat nasional yang sudah memasuki edisi ke-12 dengan tema "
            "'Break the Impossible'. Jenjang SMP mengikuti OPSILON (penyisihan & final daring), "
            "KOSA KATA (pengumpulan karya), dan KOMPAS (poster digital); LOKASI, EPIC, dan "
            "TRACTION tidak dibuka untuk SMP."
        ),
        "tgl_lomba": (
            "OPSILON penyisihan 16-17 Jan 2027, final 23-24 Jan 2027; pengumuman 31 Jan 2027"
        ),
        "deadline": "2026-12-24",
        "lokasi": "Daring (KOMPAS: pengumpulan berkas)",
        "link_daftar": "https://www.ou-festival.com/register",
        "flyer_url": "https://www.ou-festival.com/oufest12/logo.webp",
        "flyer_kind": "logo",
        "sumber_url": "https://www.ou-festival.com/",
    },
    {
        "judul": "6th Superstar Science Olympiad 2026/2027",
        "penyelenggara": "Tim Olimpiade MAN 1 Kota Batam",
        "kategori": "akademik",
        "bidang": "IPA, IPS, Matematika (soal terpadu)",
        "kelas": "7-9",
        "biaya": 65_000,
        "ringkasan": (
            "Olimpiade sains daring tingkat nasional jenjang SMP/MTs dan SMA/MA yang terdaftar "
            "di SIMT Puspresnas. Pendaftaran dibagi tiga gelombang dan biayanya naik tiap "
            "gelombang. Laporan hasil penyisihan 26 Januari 2027, final 28 Januari 2027."
        ),
        "tgl_lomba": "Penyisihan 23 Jan 2027, final 28 Jan 2027",
        "deadline": "2027-01-14",
        "lokasi": "Daring",
        "link_daftar": "https://daftar-sso.manbatam.sch.id/",
        "cp_nama": "Panitia SSO (jenjang SMP)",
        "cp_kontak": "0859-2656-2878",
        "flyer_url": "https://sso.manbatam.sch.id/images/LOGOSSO.png",
        "flyer_kind": "logo",
        "sumber_url": "https://sso.manbatam.sch.id/",
    },
    {
        "judul": "ASCIENCO 12 (South East Asia Student Science Street Olympiad) 2027",
        "penyelenggara": "PT. Olimpiadekita Prestasi Nusantara",
        "kategori": "akademik",
        "bidang": "Bahasa Inggris, Matematika, Fisika, Biologi, Ilmu Komputer",
        "kelas": "7-9",
        "biaya": 77_000,
        "ringkasan": (
            "Ajang akademik tingkat Asia Tenggara yang dikerjakan daring lewat sistem OBT, "
            "terbuka untuk SD hingga SMA dalam dua tingkatan (Intermediate dan Advanced). "
            "Pendaftaran dibagi empat gelombang plus injury time, biaya naik tiap gelombang."
        ),
        "tgl_lomba": (
            "Penyisihan 31 Jan 2027 (Intermediate) & 7 Feb 2027 (Advanced), "
            "semifinal 14 Feb 2027, final 28 Feb 2027"
        ),
        "deadline": "2027-01-18",
        "lokasi": "Daring (OBT)",
        "link_daftar": "https://olimpiadekita.com/ascienco-12",
        "flyer_url": "https://olimpiadekita.com/assets/poster/poster_1788337191.png",
        "sumber_url": (
            "https://kompetisi.in/berita/"
            "buka-pendaftaran-ascienco-12-tahun-2027-pelajar-sd-hingga-sma-bisa-ikuti-"
            "kompetisi-tingkat-asia-tenggara"
        ),
    },
)


def seed(db: Database, entries: tuple[dict[str, Any], ...] = SEED) -> list[int]:
    """Sisipkan entri yang belum ada (berdasarkan `sumber_url`). Kembalikan id baru."""
    inserted: list[int] = []
    for entry in entries:
        sumber = entry.get("sumber_url")
        if sumber and db.find_by_sumber(sumber):
            continue
        fields = dict(entry)
        fields.setdefault("status", "published")
        fields.setdefault("jenjang", "SMP")
        fields["dedup_key"] = dedup_key(entry["judul"], entry.get("penyelenggara"))
        inserted.append(db.insert(fields))
    return inserted


def main() -> None:
    """Jalankan penyisipan langsung (`python -m app.web.seed`).

    Delegasi ke CLI situs supaya pembacaan `DB_PATH` selalu satu tempat dan
    tidak perlu token Telegram / kunci LLM seperti `app.config.get_settings()`.
    """
    from app.web.__main__ import main as cli_main

    cli_main(["seed"])


if __name__ == "__main__":
    main()
