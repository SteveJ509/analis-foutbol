"""Fè rapò HTML (pou telefòn) apati analiz la ak kontèks ajan an chèche a.

Itilizasyon:
    python3 scripts/build_report.py data/analysis/arsenal-vs-chelsea.json
    python3 scripts/build_report.py data/analysis/arsenal-vs-chelsea.json --context data/context/arsenal-vs-chelsea.json
"""
import argparse
import json
from html import escape
from pathlib import Path

from config import CONTEXT_DIR, REPORTS_DIR


def e(v, default="—"):
    return escape(str(v)) if v not in (None, "") else default


def chip(r):
    cls = {"G": "w", "N": "d", "P": "l"}.get(r, "")
    return f'<span class="chip {cls}">{e(r)}</span>'


def prob_bar(home, draw, away, h_name, a_name):
    return f"""
    <div class="pbar">
      <div class="seg h" style="width:{home}%"></div><div class="seg d" style="width:{draw}%"></div><div class="seg a" style="width:{away}%"></div>
    </div>
    <div class="plabels">
      <div><b>{home}%</b><span>{e(h_name)}</span></div>
      <div><b>{draw}%</b><span>Nil</span></div>
      <div><b>{away}%</b><span>{e(a_name)}</span></div>
    </div>"""


def compare_row(label, hv, av, higher_better=True, unit=""):
    if hv is None or av is None:
        return f"<tr><td>{e(hv)}</td><th>{e(label)}</th><td>{e(av)}</td></tr>"
    total = (hv + av) or 1
    hw = round(100 * hv / total)
    better_h = hv > av if higher_better else hv < av
    better_a = av > hv if higher_better else av < hv
    return f"""<tr>
      <td class="{ 'best' if better_h else '' }">{hv}{unit}</td>
      <th>{e(label)}<div class="mini"><i style="width:{hw}%"></i></div></th>
      <td class="{ 'best' if better_a else '' }">{av}{unit}</td></tr>"""


def form_table(rows):
    body = "".join(
        f"<tr><td>{e(r['dat'][:5])}</td><td>{'🏠' if r['kote'] == 'Lakay' else '✈️'} {e(r['advèsè'])}<br><small>{e(r.get('konpetisyon'), '')}</small></td>"
        f"<td>{chip(r['rezilta'])} {e(r['skò'])}</td><td>{e(r['kònè_fè'] and int(r['kònè_fè']))}-{e(r['kònè_pran'] and int(r['kònè_pran']))}</td></tr>"
        for r in rows
    )
    return f'<table class="list"><tr><th>Dat</th><th>Advèsè</th><th>Skò</th><th>Kònè</th></tr>{body}</table>'


def absences(items):
    if not items:
        return '<p class="muted">Pa gen absans ki konfime.</p>'
    out = []
    for p in items:
        imp = (p.get("enpotans") or "").lower()
        cls = "hi" if imp.startswith("kle") or imp.startswith("wo") else ("mid" if imp.startswith("mwayen") else "")
        out.append(
            f'<li class="{cls}"><b>{e(p.get("jwè"))}</b> <span class="muted">{e(p.get("pozisyon"), "")}</span>'
            f'<br><small>{e(p.get("rezon"))} · {e(p.get("estati"), "")} · Enpòtans: {e(p.get("enpotans"))}</small></li>'
        )
    return '<ul class="abs">' + "".join(out) + "</ul>"


def auto_analysis(a):
    """Yon ti analiz otomatik an Kreyòl, lè ajan an poko ekri pa l la."""
    H, A = a["lakay"], a["deyò"]
    th, ta = a["ekip_lakay"], a["ekip_deyò"]
    sh, sa = th["rezime_10"], ta["rezime_10"]
    c, m = a["konbine"], a["modèl"]
    ph, pd, pa = c["lakay_genyen"], c["nil"], c["deyò_genyen"]
    best = max(ph, pd, pa)
    if best == pd or abs(ph - pa) < 6:
        fav = f"Match sa a sanble ekilibre: {H} {ph}%, nil {pd}%, {A} {pa}%."
    else:
        f, p = (H, ph) if ph > pa else (A, pa)
        fav = f"{f} se favori a ak {p}% chans pou genyen (nil {pd}%)."
    parts = [fav]
    parts.append(
        f"Nan 10 dènye match yo, {H} fè {sh.get('pwen', 0)} pwen ({sh.get('fòm', '')[:5]} nan 5 dènye yo) "
        f"epi {A} fè {sa.get('pwen', 0)} pwen ({sa.get('fòm', '')[:5]})."
    )
    parts.append(
        f"Atak {H}: {th['nivo_atak'].lower()} ({sh.get('mwayèn_gòl_make')} gòl/match), defans: {th['nivo_defans'].lower()} "
        f"({sh.get('mwayèn_gòl_pran')} gòl pran). Atak {A}: {ta['nivo_atak'].lower()} ({sa.get('mwayèn_gòl_make')}), "
        f"defans: {ta['nivo_defans'].lower()} ({sa.get('mwayèn_gòl_pran')})."
    )
    o25, btts = m["plis_2_5"], m["tou_de_make"]
    if o25 >= 58:
        goals = f"Modèl la prevwa yon match ak gòl: {o25}% chans pou gen plis pase 2.5 gòl"
    elif o25 <= 42:
        goals = f"Modèl la prevwa yon match fèmen: sèlman {o25}% chans pou gen plis pase 2.5 gòl"
    else:
        goals = f"Plis pase 2.5 gòl: {o25}%"
    parts.append(f"{goals}, epi {btts}% chans pou tou de ekip make.")
    kc = a.get("kònè_atann")
    if kc and kc.get("total"):
        ref = kc.get("mwayèn_chanpyona")
        cmp = ""
        if ref:
            cmp = " (plis pase mwayèn chanpyona a)" if kc["total"] > ref + 0.7 else (" (mwens pase mwayèn chanpyona a)" if kc["total"] < ref - 0.7 else " (tou pre mwayèn chanpyona a)")
        parts.append(f"Kònè atann: anviwon {kc['total']}{cmp}.")
    parts.append("Analiz otomatik sa a baze sou chif yo sèlman: li pa konnen blesi ak nouvèl dènye minit yo.")
    return " ".join(parts)


def build(a, ctx):
    H, A = a["lakay"], a["deyò"]
    th, ta = a["ekip_lakay"], a["ekip_deyò"]
    sh, sa = th["rezime_10"], ta["rezime_10"]
    kh, ka = th.get("klasman") or {}, ta.get("klasman") or {}
    m = a.get("match", {})
    c = ctx.get("prediksyon_final") or a["konbine"]
    model = a["modèl"]
    market = a.get("mache")
    stad = ctx.get("estad") or a.get("estad_done") or {}
    europe = a.get("tip") == "ewòp"

    def pos_line(t, k):
        if europe:
            loc = t.get("klasman_lokal") or {}
            parts = []
            if k.get("pozisyon"):
                parts.append(f"{k['pozisyon']}yèm faz lig")
            if loc.get("pozisyon"):
                parts.append(f"{loc['pozisyon']}yèm {t.get('chanpyona_lokal')}")
            return " · ".join(parts) or "—"
        return f"{k.get('pozisyon', '—')}yèm · {k.get('pwen', '—')} pt"

    api_inj = a.get("blesi_api") or []
    if not ctx.get("absans") and api_inj:
        absn_auto = {"lakay": [], "deyò": []}
        for x in api_inj:
            side = "lakay" if x["ekip"] == H else "deyò"
            absn_auto[side].append({"jwè": x["jwè"], "rezon": x.get("rezon"), "estati": x.get("tip"), "enpotans": "?"})
        ctx = {**ctx, "absans": absn_auto}
    absn = ctx.get("absans", {})

    # Klasman: montre ekip ki ozalantou 2 ekip yo
    table = a.get("klasman", [])
    keep = set()
    for team in (H, A):
        idx = next((i for i, r in enumerate(table) if r["ekip"] == team), None)
        if idx is not None:
            keep.update(range(max(0, idx - 2), min(len(table), idx + 3)))
    keep.update({0})
    trows = "".join(
        f'<tr class="{ "me" if r["ekip"] in (H, A) else "" }"><td>{r["pozisyon"]}</td><td>{e(r["ekip"])}</td>'
        f'<td>{r["j"]}</td><td>{r["dif"]:+d}</td><td><b>{r["pwen"]}</b></td></tr>'
        for i, r in enumerate(table) if i in keep
    )

    h2h = "".join(f"<li>{e(x['dat'])} — {e(x['lakay'])} <b>{e(x['skò'])}</b> {e(x['deyò'])}</li>" for x in a.get("fas_a_fas", []))
    scores = "".join(f'<div class="score"><b>{e(s["skò"])}</b><span>{s["pousantaj"]}%</span></div>' for s in model["skò_pi_posib"])
    sources = "".join(f'<li><a href="{escape(s.get("url", "#"))}">{e(s.get("tit"))}</a></li>' for s in ctx.get("sous", []))
    keys = "".join(f"<li>{e(k)}</li>" for k in ctx.get("pwen_kle", []))
    kc = a.get("kònè_atann", {})

    market_rows = ""
    if market:
        market_rows = f"""<tr><th>Mache (kòt)</th><td>{market['lakay_genyen']}%</td><td>{market['nil']}%</td><td>{market['deyò_genyen']}%</td></tr>
        <tr><th class="muted">Kòt mwayèn</th><td class="muted">{market['kòt']['lakay']}</td><td class="muted">{market['kòt']['nil']}</td><td class="muted">{market['kòt']['deyò']}</td></tr>"""

    venue_key_h = "5_dènye_lakay"
    venue_key_a = "5_dènye_deyò"
    vh, va = th.get(venue_key_h, {}), ta.get(venue_key_a, {})

    return f"""<!DOCTYPE html>
<html lang="ht"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(H)} vs {e(A)} — Analiz</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#14171c;--muted:#6b7280;--line:#e5e7eb;--h:#1f6feb;--d:#9ca3af;--a:#e5534b;--w:#2da44e;--l:#cf222e;--n:#bf8700}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1117;--card:#161b22;--ink:#e6edf3;--muted:#8b949e;--line:#30363d}}}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}}
main{{max-width:720px;margin:auto;padding:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:12px 0}}
h1{{font-size:1.35rem;margin:.2em 0}}h2{{font-size:1.05rem;margin:0 0 10px}}
.muted{{color:var(--muted)}}small{{color:var(--muted)}}
.head{{text-align:center}}.head .vs{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.head .team{{flex:1}}.head .team b{{display:block;font-size:1.15rem}}
.pbar{{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:10px 0 6px}}.seg.h{{background:var(--h)}}.seg.d{{background:var(--d)}}.seg.a{{background:var(--a)}}
.plabels{{display:flex;justify-content:space-between;text-align:center}}.plabels div{{flex:1}}.plabels b{{display:block;font-size:1.25rem}}.plabels span{{font-size:.8rem;color:var(--muted)}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:6px 4px;border-bottom:1px solid var(--line);text-align:center;font-weight:normal}}
.cmp th{{font-size:.85rem;color:var(--muted);width:46%}}.cmp td{{width:27%;font-weight:600}}.cmp td.best{{color:var(--w)}}
.mini{{height:4px;background:var(--a);border-radius:2px;margin-top:4px;overflow:hidden}}.mini i{{display:block;height:100%;background:var(--h)}}
.list td,.list th{{font-size:.85rem;text-align:left}}
.chip{{display:inline-block;width:22px;height:22px;line-height:22px;border-radius:6px;color:#fff;text-align:center;font-size:.75rem;font-weight:700;margin:1px}}
.chip.w{{background:var(--w)}}.chip.d{{background:var(--n)}}.chip.l{{background:var(--l)}}
.form{{margin:4px 0 10px}}
details summary{{cursor:pointer;color:var(--h);margin:6px 0}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.stat{{background:var(--bg);border-radius:10px;padding:10px;text-align:center}}.stat b{{display:block;font-size:1.3rem}}.stat span{{font-size:.8rem;color:var(--muted)}}
.scores{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.score{{background:var(--bg);border-radius:10px;padding:8px;text-align:center}}.score b{{display:block;font-size:1.1rem}}.score span{{font-size:.8rem;color:var(--muted)}}
.abs{{list-style:none;padding:0;margin:0}}.abs li{{padding:8px 10px;border-left:4px solid var(--line);margin:6px 0;background:var(--bg);border-radius:6px}}.abs li.hi{{border-color:var(--l)}}.abs li.mid{{border-color:var(--n)}}
tr.me td{{font-weight:700;background:var(--bg)}}
.verdict{{border-left:4px solid var(--h)}}
.foot{{font-size:.8rem;color:var(--muted);text-align:center;margin:20px 0}}
a{{color:var(--h)}}
</style></head><body><main>

<div class="card head">
  <div class="muted">{e(a['chanpyona']['non'])} · {e(a['chanpyona']['peyi'])}</div>
  <div class="vs"><div class="team"><b>{e(H)}</b><small>{e(pos_line(th, kh))}</small></div>
  <div class="muted">vs</div>
  <div class="team"><b>{e(A)}</b><small>{e(pos_line(ta, ka))}</small></div></div>
  <div class="muted" style="margin-top:6px">📅 {e(m.get('dat') or ctx.get('dat'))} · ⏰ {e(m.get('lè_uk') or ctx.get('lè'))}{'' if 'UTC' in str(m.get('lè_uk', '')) else ' (UK)'} · 🏟️ {e(stad.get('non'))}</div>
</div>

<div class="card">
  <h2>🎯 Chans pou genyen</h2>
  {prob_bar(c['lakay_genyen'], c['nil'], c['deyò_genyen'], H, A)}
  <small>{e(c.get('metòd'))}</small>
  <details><summary>Wè detay modèl la</summary>
  <table><tr><th></th><th>{e(H)}</th><th>Nil</th><th>{e(A)}</th></tr>
  <tr><th>Modèl Poisson</th><td>{model['lakay_genyen']}%</td><td>{model['nil']}%</td><td>{model['deyò_genyen']}%</td></tr>
  {market_rows}</table>
  <p class="muted">Gòl atann: {e(H)} {model['gòl_atann_lakay']} · {e(A)} {model['gòl_atann_deyò']}</p></details>
</div>

<div class="card verdict">
  <h2>🧠 Analiz</h2>
  <p>{e(ctx.get('analiz') or auto_analysis(a))}</p>
  {f'<ul>{keys}</ul>' if keys else ''}
  {f'<p><b>Prediksyon:</b> {e(c.get("rezon"))}</p>' if c.get('rezon') else ''}
</div>

<div class="card">
  <h2>📈 Fòm ({e(a.get('tit_fòm', '10 dènye match'))})</h2>
  <div><b>{e(H)}</b> <small>{sh.get('genyen')}G {sh.get('nil')}N {sh.get('pèdi')}P · {sh.get('pwen')} pt</small></div>
  <div class="form">{''.join(chip(x) for x in sh.get('fòm', ''))}</div>
  <div><b>{e(A)}</b> <small>{sa.get('genyen')}G {sa.get('nil')}N {sa.get('pèdi')}P · {sa.get('pwen')} pt</small></div>
  <div class="form">{''.join(chip(x) for x in sa.get('fòm', ''))}</div>
  <small>Pi resan an agoch. G = genyen, N = nil, P = pèdi.</small>
  <details><summary>10 dènye match {e(H)}</summary>{form_table(th['10_dènye_match'])}</details>
  <details><summary>10 dènye match {e(A)}</summary>{form_table(ta['10_dènye_match'])}</details>
  <p class="muted">{e(H)} lakay (5 dènye): {e(vh.get('fòm'))} · {e(A)} deyò (5 dènye): {e(va.get('fòm'))}</p>
</div>

<div class="card">
  <h2>⚔️ Atak ak 🛡️ Defans</h2>
  <div class="grid">
    <div class="stat"><span>Atak {e(H)}</span><b>{e(th['nivo_atak'])}</b></div>
    <div class="stat"><span>Atak {e(A)}</span><b>{e(ta['nivo_atak'])}</b></div>
    <div class="stat"><span>Defans {e(H)}</span><b>{e(th['nivo_defans'])}</b></div>
    <div class="stat"><span>Defans {e(A)}</span><b>{e(ta['nivo_defans'])}</b></div>
  </div>
  <table class="cmp" style="margin-top:10px">
  <tr><td><b>{e(H)}</b></td><th>mwayèn pa match (10 dènye)</th><td><b>{e(A)}</b></td></tr>
  {compare_row('Gòl make', sh.get('mwayèn_gòl_make'), sa.get('mwayèn_gòl_make'))}
  {compare_row('Gòl pran', sh.get('mwayèn_gòl_pran'), sa.get('mwayèn_gòl_pran'), higher_better=False)}
  {compare_row('xG', sh.get('mwayèn_xg'), sa.get('mwayèn_xg'))}
  {compare_row('Chout', sh.get('mwayèn_chout'), sa.get('mwayèn_chout'))}
  {compare_row('Chout kadre', sh.get('mwayèn_chout_kadre'), sa.get('mwayèn_chout_kadre'))}
  {compare_row('Chout yo pran', sh.get('mwayèn_chout_pran'), sa.get('mwayèn_chout_pran'), higher_better=False)}
  {compare_row('Pa pran gòl', sh.get('pousantaj_pa_pran_gòl'), sa.get('pousantaj_pa_pran_gòl'), unit='%')}
  {compare_row('Pa make', sh.get('pousantaj_pa_make'), sa.get('pousantaj_pa_make'), higher_better=False, unit='%')}
  {compare_row('Kat jòn', sh.get('mwayèn_kat_jòn'), sa.get('mwayèn_kat_jòn'), higher_better=False)}
  </table>
</div>

<div class="card">
  <h2>⚽ Gòl ak 🚩 Kònè</h2>
  <div class="grid">
    <div class="stat"><span>Plis 2.5 gòl (modèl)</span><b>{model['plis_2_5']}%</b></div>
    <div class="stat"><span>Tou de make (modèl)</span><b>{model['tou_de_make']}%</b></div>
    <div class="stat"><span>Plis 2.5 · {e(H)} / {e(A)}</span><b>{e(sh.get('pousantaj_plis_2_5'))}% / {e(sa.get('pousantaj_plis_2_5'))}%</b></div>
    <div class="stat"><span>Tou de make · {e(H)} / {e(A)}</span><b>{e(sh.get('pousantaj_tou_de_make'))}% / {e(sa.get('pousantaj_tou_de_make'))}%</b></div>
    <div class="stat"><span>Kònè atann (total)</span><b>{e(kc.get('total'))}</b></div>
    <div class="stat"><span>Mwayèn kònè chanpyona</span><b>{e(kc.get('mwayèn_chanpyona'))}</b></div>
  </div>
  <table class="cmp" style="margin-top:10px">
  {compare_row('Kònè fè', sh.get('mwayèn_kònè_fè'), sa.get('mwayèn_kònè_fè'))}
  {compare_row('Kònè pran', sh.get('mwayèn_kònè_pran'), sa.get('mwayèn_kònè_pran'), higher_better=False)}
  </table>
  <p class="muted">Plis 1.5: {model['plis_1_5']}% · Plis 3.5: {model['plis_3_5']}%{(' · ' + e(kc.get('nòt'))) if kc.get('nòt') else ''}</p>
</div>

<div class="card">
  <h2>🔢 Skò ki pi posib</h2>
  <div class="scores">{scores}</div>
</div>

<div class="card">
  <h2>🚑 Blesi ak absans</h2>
  <b>{e(H)}</b>{absences(absn.get('lakay'))}
  <b>{e(A)}</b>{absences(absn.get('deyò'))}
</div>

<div class="card">
  <h2>🏟️ Estad, teren ak kontèks</h2>
  <p><b>Estad:</b> {e(stad.get('non'))}, {e(stad.get('vil'))}<br>
  <b>Teren:</b> {e(stad.get('teren'))}<br>
  <b>Move tan:</b> {e(ctx.get('move_tan'))}<br>
  <b>Abit:</b> {e(m.get('abit') or ctx.get('abit'))}{('<br><b>Etap:</b> ' + e(m.get('etap'))) if m.get('etap') else ''}</p>
  <p><b>Enpòtans match la:</b> {e(ctx.get('enpotans_match'))}</p>
</div>

<div class="card">
  <h2>🏆 {e(a.get('tit_klasman', 'Klasman'))}</h2>
  <table class="list"><tr><th>#</th><th>Ekip</th><th>J</th><th>Dif</th><th>Pt</th></tr>{trows}</table>
</div>

<div class="card">
  <h2>🤝 Fas a fas</h2>
  {f'<ul>{h2h}</ul>' if h2h else '<p class="muted">Pa gen match resan nan done yo.</p>'}
</div>

{f'<div class="card"><h2>🔗 Sous</h2><ul>{sources}</ul></div>' if sources else ''}

<p class="foot">Kreye {e(a['kreye_le'])} · Done: football-data.co.uk + rechèch sou entènèt.<br>
Pousantaj yo se estimasyon, pa garanti. Si w parye, pa janm mize plis pase sa w ka pèdi.</p>
</main></body></html>"""


def build_index():
    items = []
    for p in sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        if p.name == "index.html":
            continue
        title = p.stem.replace("-vs-", " vs ").replace("-", " ").title()
        items.append(f'<li><a href="{escape(p.name)}">{escape(title)}</a></li>')
    html = f"""<!DOCTYPE html><html lang="ht"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analiz Foutbòl</title><style>body{{font:16px system-ui,sans-serif;max-width:640px;margin:auto;padding:16px}}li{{margin:10px 0}}a{{color:#1f6feb}}
@media (prefers-color-scheme:dark){{body{{background:#0d1117;color:#e6edf3}}}}</style></head>
<body><h1>⚽ Analiz Foutbòl</h1><ul>{''.join(items) or '<li>Pa gen rapò ankò.</li>'}</ul></body></html>"""
    (REPORTS_DIR / "index.html").write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis", help="Fichye JSON analiz la (data/analysis/...)")
    ap.add_argument("--context", help="Fichye JSON kontèks ajan an (data/context/...)")
    args = ap.parse_args()

    a = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    ctx_path = Path(args.context) if args.context else CONTEXT_DIR / f"{a['slug']}.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.exists() else {}
    if not ctx:
        print("⚠ Pa gen kontèks (blesi, estad, analiz). Rapò a ap gen estatistik yo sèlman.")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{a['slug']}.html"
    out.write_text(build(a, ctx), encoding="utf-8")
    build_index()
    print(f"✓ Rapò a pare: {out}")


if __name__ == "__main__":
    main()
