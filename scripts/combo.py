"""Konbinezon wikenn (5 gran chanpyona yo): youn ak kòt ~5 (pridan), youn ak kòt ~10.

Prensip (tankou yon parieur pro):
  - Chak seleksyon dwe gen omwen 85% chans (apre nou korije l ak rezilta backtest la).
  - Yon sèl seleksyon pa match (pou rezilta yo pa depann youn sou lòt).
  - Sèlman mache modèl la te reyisi byen nan tès la (pa gen "tou de make" pa egzanp).
  - Nou sote seleksyon ki twò evidan (kòt jis anba 1.05): bookmaker yo pa peye anyen pou yo.

Itilizasyon:
    python3 scripts/combo.py           # montre konbinezon wikenn nan
    python3 scripts/combo.py --json    # ekri data/combo_auto.json
"""
import json
import math
from datetime import datetime, timedelta

import model as M
from config import DATA_DIR, LEAGUES

MIN_P = 0.85
MAX_P = 0.95
TARGETS = [
    {"id": "k5", "non": "Konbinezon pridan", "sib": 5.0, "max": 12},
    {"id": "k10", "non": "Konbinezon kòt 10", "sib": 10.0, "max": 20},
]
# Mache ki kalifye pou konbinezon yo (BTTS ak rezilta sèk yo twò volatil)
ALLOWED = {"O0.5", "O1.5", "U3.5", "U4.5", "1X", "X2", "12", "DNB1", "DNB2",
           "H_O0.5", "A_O0.5", "C_O7.5", "C_O8.5", "C_U11.5", "C_U10.5"}
AUTO_PATH = DATA_DIR / "combo_auto.json"
AGENT_PATH = DATA_DIR / "context" / "konbinezon.json"


def weekend_window(now=None):
    """Vandredi 00:00 -> Lendi 23:59 wikenn kounye a (oswa k ap vini an)."""
    now = now or datetime.now()
    wd = now.weekday()  # 0 = lendi
    if wd in (4, 5, 6):
        start = now
        end = (now + timedelta(days=(7 - wd))).replace(hour=23, minute=59)
    elif wd == 0:
        start, end = now, now.replace(hour=23, minute=59)
    else:
        start = (now + timedelta(days=4 - wd)).replace(hour=0, minute=0)
        end = (start + timedelta(days=3)).replace(hour=23, minute=59)
    return start, end


def calibrated(bt, key, p):
    """Pwobabilite pridan: pi piti ant modèl la ak sa ki te rive vre nan tès la."""
    tab = (bt or {}).get("konbinezon_mache")
    if tab is not None:
        t = tab.get(key)
        if not t or t["n"] < 30 or t["reyisi"] < 85:
            return 0.0, None  # mache sa a pa t solid nan tès la: nou pa itilize l
        return min(p, t["reyisi"] / 100), {"bann": "85-95%", "reyisi": t["reyisi"], "n": t["n"]}
    note = M.calibration_note(bt, key, p)
    if note:
        return min(p, note["reyisi"] / 100), note
    return p, None


def candidate_legs(analyses, bt):
    """Pi bon seleksyon pou chak match (yon sèl pa match)."""
    legs = []
    for a, when in analyses:
        best = None
        for row in a.get("tout_mache", []):
            k = row["mache"]
            if k not in ALLOWED:
                continue
            p = row["pousantaj"] / 100
            pc, note = calibrated(bt, k, p)
            if not (MIN_P <= pc <= MAX_P):
                continue
            leg = {"match": f"{a['lakay']} vs {a['deyò']}", "slug": a["slug"],
                   "chanpyona": a["chanpyona"]["non"], "dat": when.strftime("%d/%m"), "p_modèl": round(100 * p, 1),
                   "mache": k, "non": row["non"], "pousantaj": round(100 * pc, 1),
                   "kòt_jis": round(1 / pc, 2), "tès": note}
            # Pou chak match, nou pran seleksyon ki gen pi bon kòt la toujou ≥85%:
            # konsa nou bezwen mwens match pou rive nan kòt la (mwens marj bookmaker)
            if best is None or (round(pc, 3), -p) < (best["pousantaj"] / 100, -best["p_modèl"] / 100):
                best = leg
        if best:
            legs.append(best)
    return legs


def build(legs, target, max_legs):
    """Ajoute seleksyon youn pa youn jiskaske nou rive nan kòt la, ak mwens seleksyon posib.

    Tout seleksyon yo gen ≥85% chans. Nou kòmanse ak sa ki gen pi bon kòt yo, paske
    chak seleksyon an plis ajoute marj bookmaker la ak risk erè modèl la."""
    pool = sorted(legs, key=lambda l: (l["pousantaj"], -l["p_modèl"], 0 if l["tès"] else 1))
    chosen, odds = [], 1.0
    for leg in pool:
        if odds >= target or len(chosen) >= max_legs:
            break
        chosen.append(leg)
        odds *= leg["kòt_jis"]
    if odds < target * 0.85:
        return None  # pa ase bon seleksyon wikenn sa a
    chance = math.prod(l["pousantaj"] / 100 for l in chosen)
    return {"seleksyon": chosen, "kòt_total": round(odds, 2), "chans": round(100 * chance, 1),
            "kantite": len(chosen)}


def make_combos(analyses, bt=None):
    bt = bt if bt is not None else M.load_backtest()
    legs = candidate_legs(analyses, bt)
    out = []
    used = set()
    for t in TARGETS:
        # Nou eseye pran lòt match pase konbinezon anvan an (2 chans endepandan);
        # si pa gen ase, nou ka repran menm match yo.
        c = build([l for l in legs if l["slug"] not in used], t["sib"], t["max"]) or build(legs, t["sib"], t["max"])
        if c:
            c.update({"id": t["id"], "non": t["non"], "sib": t["sib"]})
            out.append(c)
            used |= {l["slug"] for l in c["seleksyon"]}
    return out, len(legs)


def load_agent_combos(start, end):
    """Konbinezon ajan Claude la verifye (blesi, teren, enpòtans), si l la pou wikenn sa a."""
    try:
        d = json.loads(AGENT_PATH.read_text(encoding="utf-8"))
        fen = datetime.strptime(d["fen"], "%d/%m/%Y")
        if fen.date() >= start.date():
            return d
    except (OSError, ValueError, KeyError):
        pass
    return None


def main():
    import argparse
    import contextlib
    import io

    import analyze_match as am
    from footdata import load_fixtures

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="ekri data/combo_auto.json (ak tout seleksyon rezèv yo)")
    ap.add_argument("--from-agent", metavar="FICHYE", help="fè konbinezon final yo ak chwa ajan an")
    args = ap.parse_args()
    if args.from_agent:
        return finalize(args.from_agent)
    start, end = weekend_window()
    import build_site
    analyses = []
    for when, _, code, home, away, europe in build_site.upcoming(10):
        if europe or code not in LEAGUES or not (start <= when <= end):
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                a, _ = am.analyze(home, away)
            except SystemExit:
                continue
        analyses.append((a, when))
    combos, n = make_combos(analyses)
    pool = sorted(candidate_legs(analyses, M.load_backtest()), key=lambda l: -l["pousantaj"])
    print(f"Wikenn {start:%d/%m} – {end:%d/%m}: {len(analyses)} match, {n} seleksyon kalifye (≥{int(MIN_P * 100)}%)")
    for c in combos:
        print(f"\n{c['non']}: kòt jis {c['kòt_total']} · chans {c['chans']}% · {c['kantite']} seleksyon")
        for l in c["seleksyon"]:
            print(f"  {l['dat']}  {l['match']:<35} {l['non']:<40} {l['pousantaj']}%  ({l['kòt_jis']})")
    if args.json:
        AUTO_PATH.write_text(json.dumps({"kòmanse": start.strftime("%d/%m/%Y"), "fen": end.strftime("%d/%m/%Y"),
                                         "konbinezon": combos, "rezèv": pool}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n✓ {AUTO_PATH}")


def finalize(path):
    """Fichye ajan an: {"k5": [{"slug", "mache", "nòt"}], "k10": [...], "retire": [{"match", "rezon"}], "rezime": "..."}"""
    auto = json.loads(AUTO_PATH.read_text(encoding="utf-8"))
    pool = {(l["slug"], l["mache"]): l for l in auto.get("rezèv", [])}
    for c in auto.get("konbinezon", []):
        for l in c["seleksyon"]:
            pool.setdefault((l["slug"], l["mache"]), l)
    draft = json.loads(open(path, encoding="utf-8").read())
    out = []
    for t in TARGETS:
        legs = []
        for x in draft.get(t["id"], []):
            leg = pool.get((x["slug"], x["mache"]))
            if not leg:
                print(f"  ✗ Pa jwenn {x['slug']} / {x['mache']} nan combo_auto.json — sote l")
                continue
            legs.append({**leg, "nòt": x.get("nòt", "")})
        if legs:
            odds = math.prod(l["kòt_jis"] for l in legs)
            chance = math.prod(l["pousantaj"] / 100 for l in legs)
            out.append({"id": t["id"], "non": t["non"], "sib": t["sib"], "seleksyon": legs, "kantite": len(legs),
                        "kòt_total": round(odds, 2), "chans": round(100 * chance, 1)})
            print(f"  ✓ {t['non']}: {len(legs)} seleksyon, kòt jis {odds:.2f}, chans {100 * chance:.1f}%")
    final = {"kòmanse": auto["kòmanse"], "fen": auto["fen"], "verifye": True,
             "kreye_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
             "konbinezon": out, "retire": draft.get("retire", []), "rezime": draft.get("rezime", "")}
    AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_PATH.write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {AGENT_PATH}")


if __name__ == "__main__":
    main()
