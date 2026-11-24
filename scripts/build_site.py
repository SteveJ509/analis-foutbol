"""Konstwi sit la: analize tout match k ap vini yo epi kreye paj akèy la.

Itilizasyon:
    python3 scripts/build_site.py            # kreye sit la nan dosye site/
    python3 scripts/build_site.py --days 10  # match 10 jou k ap vini yo
"""
import argparse
import contextlib
import io
import json
from datetime import datetime, timedelta
from html import escape

import analyze_match as am
from build_report import build, e
from config import ALL_DOMESTIC, CONTEXT_DIR, EURO_COMPS, LEAGUES, ROOT
from config import RAW_DIR
from datetime import timezone
from footdata import all_teams, load_euro, load_fixtures, load_results, resolve_team

SITE_DIR = ROOT / "site"
INJURY_LIMIT = 20  # pou pa depase 100 demann API-Football pa jou (sit la mete ajou 2 fwa)


def upcoming(days):
    now = datetime.now()
    start, end = now - timedelta(hours=3), now + timedelta(days=days)
    out = []
    for f in load_fixtures():
        if f["div"] in LEAGUES and start <= f["date"].replace(hour=23) and f["date"] <= end:
            out.append((f["date"], f["time"] + " UK", f["div"], f["home"], f["away"], None))
    # Kalandriye football-data.org (si gen kle): match fixtures.csv poko genyen yo
    path = RAW_DIR / "upcoming_domestic.json"
    if path.exists():
        teams = all_teams(load_results())
        seen = {(x[2], x[3], x[4]) for x in out}
        for r in json.loads(path.read_text(encoding="utf-8")):
            try:
                d = datetime.fromisoformat(r["dat"].replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
            except (KeyError, ValueError, AttributeError):
                continue
            div_teams = {t: c for t, c in teams.items() if c == r["div"]}
            h = resolve_team(r.get("lakay"), div_teams, cutoff=0.75)
            a = resolve_team(r.get("deyò"), div_teams, cutoff=0.75)
            if h and a and (r["div"], h, a) not in seen and start <= d <= end:
                out.append((d, d.strftime("%H:%M") + " UTC", r["div"], h, a, None))
                seen.add((r["div"], h, a))
    for code in EURO_COMPS:
        for f in load_euro(code)[1]:
            if start <= f["date"] <= end:
                out.append((f["date"], f["time"] + " UTC", code, f["home"], f["away"], code))
    out.sort(key=lambda x: (x[0], x[2]))
    return out


def analyze_quiet(home, away, europe):
    """Lanse analiz la san li pa ekri nan terminal la; retounen None si l echwe."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            a, _ = am.analyze_europe(home, away, europe) if europe else am.analyze(home, away)
        return a
    except SystemExit as ex:
        print(f"  ✗ {home} vs {away}: {ex}")
    except Exception as ex:  # noqa: BLE001
        print(f"  ✗ {home} vs {away}: {type(ex).__name__}: {ex}")
    return None


def card(a, when, time_label, comp_name, comp_code):
    c, m = a["konbine"], a["modèl"]
    H, A = a["lakay"], a["deyò"]
    ph, pd, pa = c["lakay_genyen"], c["nil"], c["deyò_genyen"]
    picks = (a.get("rekòmandasyon") or {}).get("chwa") or []
    top = picks[0] if picks else None
    vals = (a.get("rekòmandasyon") or {}).get("value") or []
    sh = a["ekip_lakay"]["rezime_10"].get("fòm", "")[:5]
    sa = a["ekip_deyò"]["rezime_10"].get("fòm", "")[:5]
    search = escape(f"{H} {A} {comp_name}".lower())
    return f"""
<a class="card" href="m/{escape(a['slug'])}.html" data-comp="{escape(comp_code)}" data-q="{search}">
  <div class="top"><span class="tag t-{escape(comp_code)}">{e(comp_name)}</span><span class="muted">{e(time_label)}</span></div>
  <div class="teams"><div><b>{e(H)}</b><small>{e(sh)}</small></div><div><b>{e(A)}</b><small>{e(sa)}</small></div></div>
  <div class="pbar"><i class="h" style="width:{ph}%"></i><i class="d" style="width:{pd}%"></i><i class="a" style="width:{pa}%"></i></div>
  <div class="nums"><span>{ph}%</span><span>X {pd}%</span><span>{pa}%</span></div>
  <div class="meta">{('✅ <b>' + e(top['non']) + '</b> ' + str(top['pousantaj']) + '% <span class="st">' + '★' * top['etwal'] + '</span>') if top else ''}
  {('<br>💎 Value: ' + e(vals[0]['non']) + ' @ ' + str(vals[0]['kòt'])) if vals else ''}</div>
  <div class="meta">+1.5: {m['plis_1_5']}% · +2.5: {m['plis_2_5']}% · Tou de make: {m['tou_de_make']}%</div>
</a>"""


DAYS_HT = ["Lendi", "Madi", "Mèkredi", "Jedi", "Vandredi", "Samdi", "Dimanch"]
MONTHS_HT = ["", "janvye", "fevriye", "mas", "avril", "me", "jen", "jiyè", "out", "septanm", "oktòb", "novanm", "desanm"]


def day_label(d):
    return f"{DAYS_HT[d.weekday()]} {d.day} {MONTHS_HT[d.month]}"


def index_page(groups, comps, updated):
    import model as M
    bt = M.load_backtest()
    ch = (bt.get("chwa") or {}).get("tout") or {}
    bt_line = (f' · Tès modèl la: premye chwa a pase <b>{ch["reyisi"]}%</b> sou {ch["n"]} match ki deja jwe'
               if ch.get("reyisi") else "")
    chips = '<button class="chip on" data-f="all">Tout</button>' + "".join(
        f'<button class="chip" data-f="{escape(k)}">{e(v)}</button>' for k, v in comps.items()
    )
    body = ""
    for d, cards in groups:
        body += f'<h2 class="day">{e(day_label(d))}</h2><div class="grid">{"".join(cards)}</div>'
    if not body:
        body = ('<p class="empty">Pa gen match pou kounye a.<br>Kalandriye chanpyona yo parèt vandredi (pou wikenn nan) '
                'ak madi (pou match nan mitan semèn nan). Ajoute kle API yo nan GitHub pou w wè Champions League, '
                'Europa League ak kalandriye a pi bonè. Sit la ap mete ajou otomatikman.</p>')
    return f"""<!DOCTYPE html>
<html lang="ht"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>⚽ Analiz Foutbòl</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#14171c;--muted:#6b7280;--line:#e5e7eb;--h:#1f6feb;--d:#9ca3af;--a:#e5534b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1117;--card:#161b22;--ink:#e6edf3;--muted:#8b949e;--line:#30363d}}}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}}
header{{padding:18px 14px 6px;max-width:960px;margin:auto}}h1{{margin:0;font-size:1.5rem}}
main{{max-width:960px;margin:auto;padding:0 14px 30px}}
.muted{{color:var(--muted);font-size:.82rem}}
input{{width:100%;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--ink);font-size:1rem;margin:12px 0 8px}}
.chips{{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px}}
.chip{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;font-size:.85rem;white-space:nowrap;cursor:pointer}}
.chip.on{{background:var(--h);border-color:var(--h);color:#fff}}
.day{{font-size:1rem;margin:22px 0 8px;color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}}
.card{{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;color:inherit;text-decoration:none}}
.card:active{{transform:scale(.99)}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.tag{{font-size:.72rem;font-weight:600;padding:2px 8px;border-radius:6px;background:var(--bg)}}
.t-CL,.t-EL{{background:#1f6feb22;color:var(--h)}}
.teams{{display:flex;justify-content:space-between;margin:10px 0 8px;gap:10px}}.teams div:last-child{{text-align:right}}
.teams b{{display:block}}.teams small{{color:var(--muted);letter-spacing:2px;font-size:.75rem}}
.pbar{{display:flex;height:8px;border-radius:4px;overflow:hidden}}.pbar i{{display:block}}.pbar .h{{background:var(--h)}}.pbar .d{{background:var(--d)}}.pbar .a{{background:var(--a)}}
.nums{{display:flex;justify-content:space-between;font-weight:700;font-size:.9rem;margin-top:4px}}
.meta{{font-size:.8rem;color:var(--muted);margin-top:6px}}.meta b{{color:var(--ink)}}.st{{color:#d4a72c}}
.empty{{text-align:center;color:var(--muted);margin:40px 0}}
footer{{text-align:center;font-size:.78rem;color:var(--muted);padding:20px 14px 40px;max-width:640px;margin:auto}}
</style></head><body>
<header><h1>⚽ Analiz Foutbòl</h1><div class="muted">Mete ajou: {e(updated)}{bt_line} · Klike sou yon match pou w wè analiz konplè a</div>
<input id="q" type="search" placeholder="Chèche yon ekip…" autocomplete="off">
<div class="chips">{chips}</div></header>
<main id="list">{body}</main>
<footer>Done: football-data.co.uk, football-data.org, API-Football. Pousantaj yo se estimasyon ki soti nan yon modèl estatistik, pa garanti.
Si w parye, pa janm mize plis pase sa w ka pèdi.</footer>
<script>
let f='all';const q=document.getElementById('q');
function run(){{const t=q.value.trim().toLowerCase();
document.querySelectorAll('.card').forEach(c=>{{c.style.display=((f==='all'||c.dataset.comp===f)&&(!t||c.dataset.q.includes(t)))?'':'none'}});
document.querySelectorAll('.day').forEach(h=>{{const g=h.nextElementSibling;h.style.display=[...g.children].some(c=>c.style.display!=='none')?'':'none';g.style.display=h.style.display}});}}
q.addEventListener('input',run);
document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));b.classList.add('on');f=b.dataset.f;run()}});
</script></body></html>"""


BACK_LINK = '<a href="../index.html" style="display:inline-block;margin:12px 0 0 12px;color:#1f6feb;text-decoration:none">← Tout match yo</a>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=8)
    args = ap.parse_args()
    am.INJURY_BUDGET["rès"] = INJURY_LIMIT

    (SITE_DIR / "m").mkdir(parents=True, exist_ok=True)
    groups, comps, count = {}, {}, 0
    for when, time_label, code, home, away, europe in upcoming(args.days):
        a = analyze_quiet(home, away, europe)
        if not a:
            continue
        ctx_path = CONTEXT_DIR / f"{a['slug']}.json"
        ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.exists() else {}
        html = build(a, ctx).replace("<main>", "<main>" + BACK_LINK, 1)
        (SITE_DIR / "m" / f"{a['slug']}.html").write_text(html, encoding="utf-8")
        comp_name = (EURO_COMPS.get(code) or ALL_DOMESTIC[code])["non"]
        comps[code] = comp_name
        groups.setdefault(when.date(), []).append(card(a, when, time_label, comp_name, code))
        count += 1
        print(f"  ✓ {comp_name}: {a['lakay']} vs {a['deyò']}")

    order = list(EURO_COMPS) + list(LEAGUES)
    comps = {k: comps[k] for k in order if k in comps}
    updated = datetime.now().strftime("%d/%m/%Y %H:%M") + " UTC"
    (SITE_DIR / "index.html").write_text(index_page(sorted(groups.items()), comps, updated), encoding="utf-8")
    (SITE_DIR / ".nojekyll").write_text("")
    print(f"\n✓ Sit la pare: {count} match nan {SITE_DIR}/index.html")


if __name__ == "__main__":
    main()
