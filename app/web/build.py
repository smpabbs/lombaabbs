"""Render isi database jadi situs statis bergaya feed media sosial.

Halaman yang dihasilkan memakai blok caption yang sama dengan yang dikirim ke
Telegram (lihat `app.publish.formatter._blocks`), jadi isinya satu sumber dan
tidak ada teks yang dikarang khusus untuk web. Bedanya cuma pemangkasan: kanal
membuang blok opsional agar muat di `CAPTION_LIMIT` (1024 karakter), sedangkan
web menampilkan seluruh blok.
"""

from __future__ import annotations

import html
import shutil
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.publish.formatter import _blocks, _field
from app.store.db import Database
from app.textutil import clean_url, days_until, format_date_id, whatsapp_url

DEFAULT_TITLE = "InfoLomba SMP"
MEDIA_DIRNAME = "media"
#: Batas jumlah kartu yang ikut dirender, supaya halaman tidak menggemuk.
MAX_CARDS = 500

_KATEGORI_LABEL = {"akademik": "Akademik", "non-akademik": "Non-Akademik"}
_STATUS_LABEL = {"published": "Terbit", "draft": "Draf"}

_CSS = """
:root{
  --bg:#0f1419; --card:#161d24; --card2:#1d262e; --line:#26313a;
  --ink:#e8eef4; --muted:#8b9aa8; --accent:#3ba6f1; --ok:#2fbf71;
  --warn:#e8a33d; --dead:#e0565b; --radius:16px;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
}
a{color:var(--accent); text-decoration:none}
a:hover{text-decoration:underline}
.topbar{
  position:sticky; top:0; z-index:5; background:rgba(15,20,25,.92);
  backdrop-filter:blur(10px); border-bottom:1px solid var(--line);
}
.topbar .inner{
  max-width:640px; margin:0 auto; padding:12px 16px;
  display:flex; align-items:center; gap:10px;
}
.brand{font-size:17px; font-weight:600; letter-spacing:.2px}
.brand span{color:var(--accent)}
.topbar .count{margin-left:auto; color:var(--muted); font-size:13px}
main{max-width:640px; margin:0 auto; padding:16px}
.filters{
  background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  padding:12px; margin-bottom:16px;
}
.filters input{
  width:100%; padding:11px 13px; border-radius:10px; border:1px solid var(--line);
  background:var(--card2); color:var(--ink); font-size:15px; outline:none;
}
.filters input:focus{border-color:var(--accent)}
.chips{display:flex; flex-wrap:wrap; gap:8px; margin-top:10px}
.chip{
  border:1px solid var(--line); background:var(--card2); color:var(--muted);
  border-radius:999px; padding:5px 13px; font-size:13px; cursor:pointer;
  font-family:inherit;
}
.chip.on{background:var(--accent); border-color:var(--accent); color:#06131d; font-weight:600}
.card{
  background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  margin-bottom:18px; overflow:hidden;
}
.chead{display:flex; align-items:center; gap:12px; padding:14px 16px}
.avatar{
  width:44px; height:44px; flex:0 0 44px; border-radius:50%;
  display:grid; place-items:center; font-weight:700; font-size:17px; color:#06131d;
  background:linear-gradient(135deg,#5cc0ff,#2f8fd8);
}
.org{font-weight:600; line-height:1.3}
.sub{color:var(--muted); font-size:12.5px}
.badge{
  margin-left:auto; font-size:12px; font-weight:700; padding:5px 11px;
  border-radius:999px; white-space:nowrap;
}
.badge.open{background:rgba(47,191,113,.16); color:var(--ok)}
.badge.soon{background:rgba(232,163,61,.16); color:var(--warn)}
.badge.dead{background:rgba(224,86,91,.16); color:var(--dead)}
.badge.none{background:rgba(139,154,168,.16); color:var(--muted)}
.flyerwrap{
  display:flex; align-items:center; justify-content:center;
  background:var(--card2); min-height:120px;
}
.flyerwrap img{display:block; width:100%; height:auto}
.flyerwrap .missing{
  display:none; padding:34px 16px; text-align:center; color:var(--muted); font-size:13.5px;
}
.flyerwrap.nophoto .missing{display:block}
.flyerwrap.nophoto img{display:none}
.ribbon{
  display:inline-block; margin:12px 16px 0; font-size:11.5px; font-weight:700;
  letter-spacing:.6px; text-transform:uppercase; color:var(--muted);
  border:1px solid var(--line); border-radius:6px; padding:2px 8px;
}
.ribbon.published{color:var(--ok); border-color:rgba(47,191,113,.4)}
.body{padding:12px 16px 4px}
.line{margin:0 0 5px; white-space:pre-wrap; word-wrap:break-word}
.line:first-child{font-size:16.5px; font-weight:600}
.actions{display:flex; flex-wrap:wrap; gap:8px; padding:12px 16px 6px}
.btn{
  display:inline-block; padding:9px 15px; border-radius:10px; font-size:13.5px;
  font-weight:600; border:1px solid var(--line); background:var(--card2); color:var(--ink);
}
.btn:hover{text-decoration:none; border-color:var(--accent)}
.btn.primary{background:rgba(59,166,241,.16); border-color:rgba(59,166,241,.45); color:#88cdfb}
.src{padding:6px 16px 15px; font-size:12px; color:var(--muted); word-break:break-all}
.closed{opacity:.6}
.card.expired{opacity:.62}
.toggle{
  margin-top:10px; border:1px dashed var(--line); background:transparent; color:var(--muted);
  border-radius:999px; padding:5px 13px; font-size:13px; cursor:pointer; font-family:inherit;
}
.toggle.on{color:var(--accent); border-color:var(--accent)}
.note{
  color:var(--muted); font-size:13px; text-align:center; padding:8px 0 28px; line-height:1.6;
}
.empty{
  background:var(--card); border:1px dashed var(--line); border-radius:var(--radius);
  padding:38px 20px; text-align:center; color:var(--muted);
}
"""

_JS = """
(function(){
  var q=document.getElementById('q'), chips=document.querySelectorAll('.chip');
  var cards=document.querySelectorAll('.card'), empty=document.getElementById('empty');
  var toggle=document.getElementById('showClosed');
  var kategori='semua', showClosed=false;
  function apply(){
    var term=(q.value||'').toLowerCase().trim(), shown=0;
    cards.forEach(function(c){
      var okTerm=!term || (c.dataset.text||'').indexOf(term)!==-1;
      var okKat=kategori==='semua' || (c.dataset.kategori||'')===kategori;
      var okOpen=showClosed || !c.classList.contains('expired');
      var show=okTerm && okKat && okOpen;
      c.hidden=!show;
      if(show){shown++;}
    });
    empty.hidden=shown>0;
  }
  q.addEventListener('input',apply);
  chips.forEach(function(ch){
    ch.addEventListener('click',function(){
      kategori=ch.dataset.kategori;
      chips.forEach(function(o){o.classList.toggle('on',o===ch);});
      apply();
    });
  });
  if(toggle){
    toggle.addEventListener('click',function(){
      showClosed=!showClosed;
      toggle.classList.toggle('on',showClosed);
      toggle.setAttribute('aria-pressed',showClosed?'true':'false');
      toggle.textContent=showClosed
        ?'Sembunyikan yang sudah tutup'
        :'Tampilkan yang sudah tutup';
      apply();
    });
  }
  apply();
})();
"""


def _esc(value: Any) -> str:
    """Escape nilai apa pun untuk disisipkan ke HTML."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _media_url(row: Any, media_dirname: str) -> str | None:
    """URL gambar salinan lokal, kalau flyer disimpan di disk."""
    local = _field(row, "flyer_local_path")
    if not local:
        return None
    return f"{media_dirname}/{Path(str(local)).name}"


def _badge(remaining: int | None) -> tuple[str, str]:
    """Label + kelas CSS penanda sisa waktu pendaftaran."""
    if remaining is None:
        return "Tanpa deadline", "none"
    if remaining < 0:
        return "Pendaftaran ditutup", "dead"
    if remaining == 0:
        return "Hari ini terakhir", "dead"
    if remaining <= 7:
        return f"Sisa {remaining} hari", "soon"
    return f"Sisa {remaining} hari", "open"


def _card_text(row: Any) -> str:
    """Teks untuk pencarian sisi klien (judul, penyelenggara, bidang, ringkasan)."""
    parts = [
        _field(row, "judul"),
        _field(row, "penyelenggara"),
        _field(row, "bidang"),
        _field(row, "ringkasan"),
        _field(row, "lokasi"),
        _field(row, "hadiah"),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def render_card(row: Any, *, today: date, media_dirname: str = MEDIA_DIRNAME) -> str:
    """Satu kartu bergaya postingan media sosial."""
    judul = _field(row, "judul") or "Info Lomba SMP"
    penyelenggara = _field(row, "penyelenggara") or "Penyelenggara tidak diketahui"
    kategori = _field(row, "kategori")
    status = _field(row, "status") or "draft"

    remaining = days_until(_field(row, "deadline"), today)
    badge_label, badge_class = _badge(remaining)
    avatar_letter = next((ch for ch in penyelenggara if ch.isalnum()), "?")

    meta_bits = [bit for bit in (_field(row, "bidang"), _field(row, "lokasi")) if bit]
    if deadline := format_date_id(_field(row, "deadline")):
        meta_bits.append(f"Tutup {deadline}")
    meta = " · ".join(str(bit) for bit in meta_bits) or "Info lomba SMP"

    # Sama seperti link daftar/sumber: flyer_url pun berasal dari data ekstraksi,
    # jadi skema selain http(s) ditolak sebelum masuk ke atribut src.
    flyer = _media_url(row, media_dirname) or clean_url(_field(row, "flyer_url"))
    # Sebagian penyelenggara belum merilis poster resmi; yang resmi tersedia hanya
    # logo. Gambar tetap ditampilkan apa adanya, tapi labelnya menyebut logo secara
    # jujur alih-alih mengakuinya sebagai flyer.
    if str(_field(row, "flyer_kind") or "") == "logo":
        caption = f"Logo resmi {judul}"
        missing = "Poster resmi belum dirilis — yang tampil adalah logo resmi penyelenggara"
    else:
        caption = f"Flyer resmi {judul}"
        missing = "Flyer resmi dari penyelenggara belum tersedia"
    if flyer:
        flyer_html = (
            '<div class="flyerwrap">'
            f'<img src="{_esc(flyer)}" alt="{_esc(caption)}" '
            'loading="lazy" referrerpolicy="no-referrer" '
            "onerror=\"this.closest('.flyerwrap').classList.add('nophoto')\">"
            f'<span class="missing">{_esc(missing)}</span>'
            "</div>"
        )
    else:
        flyer_html = (
            '<div class="flyerwrap nophoto">'
            '<span class="missing">Flyer resmi dari penyelenggara belum tersedia'
            "<br>(bot tidak pernah membuat flyer sendiri)</span>"
            "</div>"
        )

    lines = "".join(
        f'<p class="line">{_esc(block["text"])}</p>' for block in _blocks(row, today)
    )

    # Isi kolom berasal dari hasil ekstraksi LLM, jadi URL divalidasi lagi di
    # sini agar skema seperti `javascript:` tidak pernah jadi href.
    daftar = clean_url(_field(row, "link_daftar"))
    sumber = clean_url(_field(row, "sumber_url"))

    buttons = []
    if daftar:
        buttons.append(
            f'<a class="btn primary" href="{_esc(daftar)}" target="_blank" '
            f'rel="noopener noreferrer">🔗 Daftar</a>'
        )
    if wa := whatsapp_url(_field(row, "cp_wa") or _field(row, "cp_kontak")):
        buttons.append(
            f'<a class="btn" href="{_esc(wa)}" target="_blank" '
            f'rel="noopener noreferrer">📞 Chat CP</a>'
        )
    if sumber:
        buttons.append(
            f'<a class="btn" href="{_esc(sumber)}" target="_blank" '
            f'rel="noopener noreferrer">📄 Sumber</a>'
        )
    actions = f'<div class="actions">{"".join(buttons)}</div>' if buttons else ""

    source_line = ""
    if sumber:
        source_line = f'<div class="src">Asal: <a href="{_esc(sumber)}">{_esc(sumber)}</a></div>'

    status_label = _STATUS_LABEL.get(str(status), "Draf")

    # Lomba yang pendaftarannya sudah lewat tetap ikut dirender, tapi ditandai
    # kelas `expired` supaya bisa disembunyikan secara default di sisi klien.
    classes = ["card"]
    if remaining is not None and remaining < 0:
        classes.append("expired")
    if str(status) != "published":
        classes.append("closed")

    return (
        f'<article class="{" ".join(classes)}" data-kategori="{_esc(kategori)}" '
        f'data-text="{_esc(_card_text(row))}">'
        '<div class="chead">'
        f'<div class="avatar">{_esc(avatar_letter.upper())}</div>'
        "<div>"
        f'<div class="org">{_esc(penyelenggara)}</div>'
        f'<div class="sub">{_esc(meta)}</div>'
        "</div>"
        f'<div class="badge {badge_class}">{_esc(badge_label)}</div>'
        "</div>"
        f'<span class="ribbon {_esc(status)}">{_esc(status_label)}</span>'
        f"{flyer_html}"
        f'<div class="body">{lines}</div>'
        f"{actions}"
        f"{source_line}"
        "</article>"
    )


def _chips(rows: Sequence[Any]) -> str:
    """Tombol filter kategori, hanya untuk kategori yang memang ada isinya."""
    present = sorted({str(_field(row, "kategori")) for row in rows if _field(row, "kategori")})
    chips = ['<button class="chip on" data-kategori="semua">Semua</button>']
    chips.extend(
        f'<button class="chip" data-kategori="{_esc(key)}">'
        f"{_esc(_KATEGORI_LABEL.get(key, key.title()))}</button>"
        for key in present
    )
    return f'<div class="chips">{"".join(chips)}</div>'


def render_page(
    rows: Sequence[Any],
    *,
    today: date | None = None,
    title: str = DEFAULT_TITLE,
    media_dirname: str = MEDIA_DIRNAME,
    generated_at: datetime | None = None,
) -> str:
    """Halaman HTML lengkap berisi kartu-kartu lomba."""
    today = today or date.today()
    generated_at = generated_at or datetime.now()
    stamp = generated_at.strftime("%d %b %Y %H:%M")

    if rows:
        cards = "".join(render_card(row, today=today, media_dirname=media_dirname) for row in rows)
        count = f"{len(rows)} lomba"
    else:
        cards = ""
        count = "belum ada data"

    return f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<meta name="description" content="Kumpulan info lomba jenjang SMP.">
<style>{_CSS}</style>
</head>
<body>
<div class="topbar"><div class="inner">
  <div class="brand">🎓 InfoLomba <span>SMP</span></div>
  <div class="count">{_esc(count)}</div>
</div></div>
<main>
  <div class="filters">
    <input id="q" type="search" placeholder="Cari lomba, penyelenggara, atau bidang…"
           autocomplete="off">
    {_chips(rows)}
    <button class="toggle" id="showClosed" type="button" aria-pressed="false">
      Tampilkan yang sudah tutup
    </button>
  </div>
  <div id="feed">{cards}</div>
  <div class="empty" id="empty" hidden>Tidak ada lomba yang cocok dengan pencarian itu.</div>
  <p class="note">
    Dibuat otomatis dari basis data InfoLomba pada {_esc(stamp)}.
    Flyer ditampilkan apa adanya dari penyelenggara — tidak pernah dibuat sendiri.
  </p>
</main>
<script>{_JS}</script>
</body>
</html>
"""


def build_site(
    db: Database,
    out_dir: str | Path,
    *,
    media_dir: str | Path | None = None,
    today: date | None = None,
    title: str = DEFAULT_TITLE,
    limit: int = MAX_CARDS,
) -> Path:
    """Tulis `index.html` (plus salinan flyer) dan kembalikan path filenya."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    media_dirname = MEDIA_DIRNAME

    rows = [row for row in db.recent(limit=limit) if str(_field(row, "status")) != "rejected"]

    if media_dir and rows:
        target = out / media_dirname
        source_root = Path(media_dir)
        copied = 0
        for row in rows:
            local = _field(row, "flyer_local_path")
            if not local:
                continue
            source = Path(str(local))
            if not source.is_file():
                source = source_root / source.name
            if not source.is_file():
                continue
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target / source.name)
            copied += 1
        if not copied and target.is_dir():
            shutil.rmtree(target, ignore_errors=True)

    index = out / "index.html"
    index.write_text(
        render_page(rows, today=today, title=title, media_dirname=media_dirname),
        encoding="utf-8",
    )
    return index
