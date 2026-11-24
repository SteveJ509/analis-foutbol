"""Analize yon match: fòm, atak/defans, kònè, klasman, modèl Poisson ak kòt mache a.

Itilizasyon:
    python3 scripts/analyze_match.py "Arsenal" "Chelsea"
    python3 scripts/analyze_match.py --list-teams
    python3 scripts/analyze_match.py --fixtures          # match k ap vini yo
    python3 scripts/analyze_match.py "Arsenal" "Bayern Munich" --europe CL
    python3 scripts/analyze_match.py "Roma" "Porto" --europe EL
"""
import argparse
import json
import math
import re
import sys
from datetime import datetime

from config import ALL_DOMESTIC, ANALYSIS_DIR, DEFAULT_STRENGTH, EURO_COMPS, LEAGUE_STRENGTH, LEAGUES, load_env
from footdata import all_teams, load_euro, load_fixtures, load_results, resolve_team

N_FORM = 10
INJURY_BUDGET = {"rès": 1000}  # build_site.py mete yon limit pou pa depase 100 demann/jou
N_STRENGTH = 20
MAX_GOALS = 10


def slugify(text):
    from footdata import norm
    text = norm(text).replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def mean(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def pct(count, total):
    return round(100 * count / total) if total else None


# ---------- Match yon ekip ----------

def team_view(m, team):
    """Wè yon match selon pwen de vi yon ekip."""
    home = m["home"] == team
    comp = EURO_COMPS.get(m["div"], ALL_DOMESTIC.get(m["div"], {})).get("non", m["div"])
    p = "h" if home else "a"
    o = "a" if home else "h"
    gf, ga = m[f"{p}g"], m[f"{o}g"]
    res = "G" if gf > ga else ("N" if gf == ga else "P")  # Genyen / Nil / Pèdi
    return {
        "dat": m["date"].strftime("%d/%m/%Y"),
        "advèsè": m["away"] if home else m["home"],
        "kote": "Lakay" if home else "Deyò",
        "konpetisyon": comp,
        "skò": f"{int(gf)}-{int(ga)}",
        "rezilta": res,
        "gòl_make": gf, "gòl_pran": ga,
        "kònè_fè": m[f"{p}c"], "kònè_pran": m[f"{o}c"],
        "chout": m[f"{p}s"], "chout_kadre": m[f"{p}st"],
        "chout_pran": m[f"{o}s"],
        "xg": m[f"{p}xg"], "xg_pran": m[f"{o}xg"],
        "kat_jòn": m[f"{p}y"], "kat_wouj": m[f"{p}r"],
    }


def team_matches(matches, team):
    return [m for m in matches if team in (m["home"], m["away"])]


def summarize(views):
    n = len(views)
    if not n:
        return {}
    w = sum(v["rezilta"] == "G" for v in views)
    d = sum(v["rezilta"] == "N" for v in views)
    l = n - w - d
    total_goals = [v["gòl_make"] + v["gòl_pran"] for v in views]
    corners_total = [
        (v["kònè_fè"] or 0) + (v["kònè_pran"] or 0)
        for v in views if v["kònè_fè"] is not None and v["kònè_pran"] is not None
    ]
    return {
        "match": n,
        "fòm": "".join(v["rezilta"] for v in reversed(views)),  # pi resan an premye
        "genyen": w, "nil": d, "pèdi": l,
        "pwen": 3 * w + d,
        "mwayèn_gòl_make": mean(v["gòl_make"] for v in views),
        "mwayèn_gòl_pran": mean(v["gòl_pran"] for v in views),
        "mwayèn_kònè_fè": mean(v["kònè_fè"] for v in views),
        "mwayèn_kònè_pran": mean(v["kònè_pran"] for v in views),
        "mwayèn_kònè_total": mean(corners_total),
        "mwayèn_chout": mean(v["chout"] for v in views),
        "mwayèn_chout_kadre": mean(v["chout_kadre"] for v in views),
        "mwayèn_chout_pran": mean(v["chout_pran"] for v in views),
        "mwayèn_xg": mean(v["xg"] for v in views),
        "mwayèn_xg_pran": mean(v["xg_pran"] for v in views),
        "mwayèn_kat_jòn": mean(v["kat_jòn"] for v in views),
        "pousantaj_plis_2_5": pct(sum(g > 2.5 for g in total_goals), n),
        "pousantaj_tou_de_make": pct(sum(v["gòl_make"] > 0 and v["gòl_pran"] > 0 for v in views), n),
        "pousantaj_pa_pran_gòl": pct(sum(v["gòl_pran"] == 0 for v in views), n),
        "pousantaj_pa_make": pct(sum(v["gòl_make"] == 0 for v in views), n),
    }


# ---------- Chanpyona ----------

def league_averages(matches):
    current = max(m["season"] for m in matches)
    sample = [m for m in matches if m["season"] == current]
    if len(sample) < 50:
        sample = matches
    n = len(sample)
    home = sum(m["hg"] for m in sample) / n
    away = sum(m["ag"] for m in sample) / n
    corners = [m["hc"] + m["ac"] for m in sample if m["hc"] is not None and m["ac"] is not None]
    return {
        "match": n,
        "gòl_lakay": round(home, 2),
        "gòl_deyò": round(away, 2),
        "gòl_pa_match": round(home + away, 2),
        "kònè_pa_match": round(sum(corners) / len(corners), 2) if corners else None,
        "pousantaj_lakay_genyen": pct(sum(m["hg"] > m["ag"] for m in sample), n),
        "pousantaj_nil": pct(sum(m["hg"] == m["ag"] for m in sample), n),
    }


def standings(matches):
    current = max(m["season"] for m in matches)
    table = {}
    for m in matches:
        if m["season"] != current:
            continue
        for team, gf, ga in ((m["home"], m["hg"], m["ag"]), (m["away"], m["ag"], m["hg"])):
            t = table.setdefault(team, {"ekip": team, "j": 0, "g": 0, "n": 0, "p": 0, "bp": 0, "bc": 0, "pwen": 0})
            t["j"] += 1
            t["bp"] += gf
            t["bc"] += ga
            if gf > ga:
                t["g"] += 1
                t["pwen"] += 3
            elif gf == ga:
                t["n"] += 1
                t["pwen"] += 1
            else:
                t["p"] += 1
    rows = sorted(table.values(), key=lambda t: (-t["pwen"], -(t["bp"] - t["bc"]), -t["bp"]))
    for i, t in enumerate(rows, 1):
        t["pozisyon"] = i
        t["dif"] = int(t["bp"] - t["bc"])
        t["bp"], t["bc"] = int(t["bp"]), int(t["bc"])
    return rows


def table_context(rows, team):
    pos = next((r for r in rows if r["ekip"] == team), None)
    if not pos:
        return None
    n = len(rows)
    leader = rows[0]["pwen"]
    fourth = rows[3]["pwen"] if n >= 4 else None
    safe_line = rows[n - 4]["pwen"] if n >= 4 else None  # dènye plas ki pa nan zòn desant (3 dènye)
    return {
        **pos,
        "kantite_ekip": n,
        "pwen_dèyè_premye": leader - pos["pwen"],
        "pwen_kont_4yèm": pos["pwen"] - fourth if fourth is not None else None,
        "pwen_anwo_zòn_desant": pos["pwen"] - rows[n - 3]["pwen"] if n >= 3 else None,
        "pwen_kont_plas_sove": pos["pwen"] - safe_line if safe_line is not None else None,
    }


# ---------- Modèl Poisson ----------

def strength(matches, team, lg, shrink=4):
    recent = team_matches(matches, team)[-N_STRENGTH:]
    scored = conceded = exp_scored = exp_conceded = 0.0
    for m in recent:
        if m["home"] == team:
            scored += m["hg"]; conceded += m["ag"]
            exp_scored += lg["gòl_lakay"]; exp_conceded += lg["gòl_deyò"]
        else:
            scored += m["ag"]; conceded += m["hg"]
            exp_scored += lg["gòl_deyò"]; exp_conceded += lg["gòl_lakay"]
    n = len(recent)
    att = scored / exp_scored if exp_scored else 1.0
    dfn = conceded / exp_conceded if exp_conceded else 1.0
    # Rale valè yo tou piti vè 1 lè pa gen anpil match
    att = (n * att + shrink) / (n + shrink)
    dfn = (n * dfn + shrink) / (n + shrink)
    return round(att, 3), round(dfn, 3), n


def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_model(lam_h, lam_a):
    ph = [poisson_pmf(k, lam_h) for k in range(MAX_GOALS + 1)]
    pa = [poisson_pmf(k, lam_a) for k in range(MAX_GOALS + 1)]
    grid = [[ph[i] * pa[j] for j in range(MAX_GOALS + 1)] for i in range(MAX_GOALS + 1)]
    total = sum(map(sum, grid))
    home = sum(grid[i][j] for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1) if i > j) / total
    draw = sum(grid[i][i] for i in range(MAX_GOALS + 1)) / total
    away = 1 - home - draw

    def over(line):
        return sum(grid[i][j] for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1) if i + j > line) / total

    btts = sum(grid[i][j] for i in range(1, MAX_GOALS + 1) for j in range(1, MAX_GOALS + 1)) / total
    scores = sorted(
        ((f"{i}-{j}", grid[i][j] / total) for i in range(6) for j in range(6)),
        key=lambda x: -x[1],
    )[:6]
    r = lambda x: round(100 * x, 1)  # noqa: E731
    return {
        "gòl_atann_lakay": round(lam_h, 2),
        "gòl_atann_deyò": round(lam_a, 2),
        "lakay_genyen": r(home), "nil": r(draw), "deyò_genyen": r(away),
        "plis_1_5": r(over(1.5)), "plis_2_5": r(over(2.5)), "plis_3_5": r(over(3.5)),
        "tou_de_make": r(btts),
        "skò_pi_posib": [{"skò": s, "pousantaj": r(p)} for s, p in scores],
    }


def implied(odds):
    vals = [o for o in odds if o]
    if len(vals) != len(odds):
        return None
    inv = [1 / o for o in odds]
    s = sum(inv)
    return [round(100 * x / s, 1) for x in inv]


def rating(value, league_value, higher_is_better=True):
    if value is None or not league_value:
        return "Pa konnen"
    ratio = value / league_value
    if not higher_is_better:
        ratio = 1 / ratio if ratio else 9
    if ratio >= 1.25:
        return "Trè fò"
    if ratio >= 1.08:
        return "Fò"
    if ratio > 0.92:
        return "Mwayen"
    if ratio > 0.78:
        return "Fèb"
    return "Trè fèb"


# ---------- Analiz prensipal ----------

def analyze(home_in, away_in):
    results = load_results()
    if not any(results.values()):
        sys.exit("Pa gen done. Lanse anvan: python3 scripts/fetch_data.py")
    teams = all_teams(results)
    home = resolve_team(home_in, teams)
    away = resolve_team(away_in, teams)
    if not home or not away:
        missing = home_in if not home else away_in
        sys.exit(f"Pa jwenn ekip '{missing}'. Gade non yo ak: python3 scripts/analyze_match.py --list-teams")
    code = teams[home]
    if teams[away] != code:
        sys.exit(f"{home} ak {away} pa nan menm chanpyona. Zouti sa a analize match chanpyona sèlman.")
    matches = results[code]
    lg = league_averages(matches)
    team_avg_goals = lg["gòl_pa_match"] / 2

    out = {
        "kreye_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "chanpyona": {"kòd": code, **ALL_DOMESTIC[code]},
        "tip": "chanpyona",
        "tit_fòm": "10 dènye match chanpyona",
        "lakay": home,
        "deyò": away,
        "mwayèn_chanpyona": lg,
    }

    # Match ki pral jwe a (dat, lè, kòt)
    fixture = next((f for f in load_fixtures() if f["home"] == home and f["away"] == away), None)
    if fixture:
        out["match"] = {"dat": fixture["date"].strftime("%d/%m/%Y"), "lè_uk": fixture["time"], "abit": fixture["referee"]}

    rows = standings(matches)
    out["klasman"] = [{k: r[k] for k in ("pozisyon", "ekip", "j", "g", "n", "p", "bp", "bc", "dif", "pwen")} for r in rows]

    for side, team in (("ekip_lakay", home), ("ekip_deyò", away)):
        tm = team_matches(matches, team)
        views = [team_view(m, team) for m in tm]
        last10 = views[-N_FORM:]
        venue = [v for v in views if v["kote"] == ("Lakay" if side == "ekip_lakay" else "Deyò")][-5:]
        s10 = summarize(last10)
        out[side] = {
            "non": team,
            "klasman": table_context(rows, team),
            "10_dènye_match": list(reversed(last10)),
            "rezime_10": s10,
            "5_dènye_" + ("lakay" if side == "ekip_lakay" else "deyò"): summarize(venue),
            "nivo_atak": rating(s10.get("mwayèn_gòl_make"), team_avg_goals),
            "nivo_defans": rating(s10.get("mwayèn_gòl_pran"), team_avg_goals, higher_is_better=False),
        }

    # Fas a fas
    h2h = [m for m in matches if {m["home"], m["away"]} == {home, away}][-6:]
    out["fas_a_fas"] = [
        {"dat": m["date"].strftime("%d/%m/%Y"), "lakay": m["home"], "deyò": m["away"], "skò": f"{int(m['hg'])}-{int(m['ag'])}"}
        for m in reversed(h2h)
    ]

    # Modèl
    att_h, def_h, n_h = strength(matches, home, lg)
    att_a, def_a, n_a = strength(matches, away, lg)
    lam_h = att_h * def_a * lg["gòl_lakay"]
    lam_a = att_a * def_h * lg["gòl_deyò"]
    model = poisson_model(lam_h, lam_a)
    model["fòs"] = {"atak_lakay": att_h, "defans_lakay": def_h, "atak_deyò": att_a, "defans_deyò": def_a,
                    "match_itilize": [n_h, n_a]}
    out["modèl"] = model

    # Kònè atann
    sh, sa = out["ekip_lakay"]["rezime_10"], out["ekip_deyò"]["rezime_10"]
    if sh.get("mwayèn_kònè_fè") is not None and sa.get("mwayèn_kònè_pran") is not None:
        ch = (sh["mwayèn_kònè_fè"] + sa["mwayèn_kònè_pran"]) / 2
        ca = (sa["mwayèn_kònè_fè"] + sh["mwayèn_kònè_pran"]) / 2
        out["kònè_atann"] = {"lakay": round(ch, 1), "deyò": round(ca, 1), "total": round(ch + ca, 1),
                             "mwayèn_chanpyona": lg["kònè_pa_match"]}

    # Mache (kòt bookmaker yo)
    if fixture:
        imp = implied([fixture["odds_h"], fixture["odds_d"], fixture["odds_a"]])
        ou = implied([fixture["odds_o25"], fixture["odds_u25"]])
        if imp:
            out["mache"] = {
                "kòt": {"lakay": fixture["odds_h"], "nil": fixture["odds_d"], "deyò": fixture["odds_a"]},
                "lakay_genyen": imp[0], "nil": imp[1], "deyò_genyen": imp[2],
                "plis_2_5": ou[0] if ou else None,
            }
            out["konbine"] = {
                "metòd": "50% modèl Poisson + 50% mache",
                "lakay_genyen": round((model["lakay_genyen"] + imp[0]) / 2, 1),
                "nil": round((model["nil"] + imp[1]) / 2, 1),
                "deyò_genyen": round((model["deyò_genyen"] + imp[2]) / 2, 1),
            }
    if "konbine" not in out:
        out["konbine"] = {"metòd": "Modèl Poisson sèlman (pa gen kòt)",
                          "lakay_genyen": model["lakay_genyen"], "nil": model["nil"], "deyò_genyen": model["deyò_genyen"]}

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    slug = f"{slugify(home)}-vs-{slugify(away)}"
    out["slug"] = slug
    path = ANALYSIS_DIR / f"{slug}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, path


# ---------- Koup Ewòp (Champions League / Europa League) ----------

def _euro_strength(team, dom_code, dom_matches, euro_done, euro_lg):
    """Fòs atak/defans: chanpyona lokal la si nou genyen l, sinon match Ewòp yo."""
    if dom_code and dom_matches:
        lg = league_averages(dom_matches)
        att, dfn, n = strength(dom_matches, team, lg)
        return att, dfn, n, "chanpyona lokal"
    att, dfn, n = strength(euro_done, team, euro_lg)
    return att, dfn, n, "match Ewòp"


def analyze_europe(home_in, away_in, comp_code):
    comp = EURO_COMPS[comp_code]
    euro_done, euro_up = load_euro(comp_code)
    if not euro_done and not euro_up:
        sys.exit(f"Pa gen done {comp['non']}. Mete kle API yo nan .env epi lanse: python3 scripts/fetch_europe.py")
    euro_teams = {t: comp_code for m in euro_done + euro_up for t in (m["home"], m["away"])}
    eh, ea = resolve_team(home_in, euro_teams), resolve_team(away_in, euro_teams)
    if not eh or not ea:
        missing = home_in if not eh else away_in
        sys.exit(f"Pa jwenn '{missing}' nan {comp['non']}. Gade non yo ak: python3 scripts/analyze_match.py --list-teams")

    results = load_results()
    dom_teams = all_teams(results)
    # Tout match Ewòp sezon sa a (CL + EL) pou fòm nan
    all_euro = []
    for c in EURO_COMPS:
        all_euro += load_euro(c)[0]

    n = len(euro_done)
    euro_lg = {
        "match": n,
        "gòl_lakay": round(sum(m["hg"] for m in euro_done) / n, 2) if n >= 20 else 1.55,
        "gòl_deyò": round(sum(m["ag"] for m in euro_done) / n, 2) if n >= 20 else 1.20,
        "kònè_pa_match": None,
    }
    euro_lg["gòl_pa_match"] = round(euro_lg["gòl_lakay"] + euro_lg["gòl_deyò"], 2)

    out = {
        "kreye_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "chanpyona": {"kòd": comp_code, "non": comp["non"], "peyi": comp["peyi"]},
        "tip": "ewòp",
        "tit_fòm": "10 dènye match (tout konpetisyon)",
        "lakay": eh, "deyò": ea,
        "mwayèn_chanpyona": euro_lg,
    }

    fixture = next((f for f in euro_up if f["home"] == eh and f["away"] == ea), None)
    if not fixture and any(f["home"] == ea and f["away"] == eh for f in euro_up):
        print(f"⚠ Nan kalandriye a, se {ea} ki resevwa. Lanse l ankò ak ekip yo nan lòt sans lan.")
    if fixture:
        out["match"] = {"dat": fixture["date"].strftime("%d/%m/%Y"), "lè_uk": fixture["time"] + " UTC",
                        "etap": fixture["stage"], "abit": ""}
        out["estad_done"] = {"non": fixture.get("venue"), "vil": fixture.get("city")}

    league_phase = [m for m in euro_done if "league" in m["stage"].lower()]
    rows = standings(league_phase) if league_phase else []
    out["klasman"] = [{k: r[k] for k in ("pozisyon", "ekip", "j", "g", "n", "p", "bp", "bc", "dif", "pwen")} for r in rows]
    out["tit_klasman"] = f"Klasman faz lig {comp['non']}"

    strengths = {}
    for side, team in (("ekip_lakay", eh), ("ekip_deyò", ea)):
        dom_name = resolve_team(team, dom_teams, cutoff=0.8)
        dom_code = dom_teams.get(dom_name) if dom_name else None
        dom_matches = results.get(dom_code, []) if dom_code else []
        views = [team_view(m, dom_name) for m in team_matches(dom_matches, dom_name)] if dom_name else []
        views += [team_view(m, team) for m in team_matches(all_euro, team)]
        views.sort(key=lambda v: datetime.strptime(v["dat"], "%d/%m/%Y"))
        last10 = views[-N_FORM:]
        venue = [v for v in views if v["kote"] == ("Lakay" if side == "ekip_lakay" else "Deyò")][-5:]
        s10 = summarize(last10)
        ref = (league_averages(dom_matches)["gòl_pa_match"] / 2) if dom_matches else euro_lg["gòl_pa_match"] / 2
        dom_table = standings(dom_matches) if dom_matches else []
        out[side] = {
            "non": team,
            "non_lokal": dom_name,
            "chanpyona_lokal": ALL_DOMESTIC[dom_code]["non"] if dom_code else None,
            "klasman": table_context(rows, team) if rows else None,
            "klasman_lokal": table_context(dom_table, dom_name) if dom_table else None,
            "10_dènye_match": list(reversed(last10)),
            "rezime_10": s10,
            "5_dènye_" + ("lakay" if side == "ekip_lakay" else "deyò"): summarize(venue),
            "nivo_atak": rating(s10.get("mwayèn_gòl_make"), ref),
            "nivo_defans": rating(s10.get("mwayèn_gòl_pran"), ref, higher_is_better=False),
        }
        if dom_code:
            att, dfn, nm, basis = _euro_strength(dom_name, dom_code, dom_matches, [], euro_lg)
        else:
            att, dfn, nm, basis = _euro_strength(team, None, [], euro_done, euro_lg)
        strengths[side] = (att, dfn, nm, basis, LEAGUE_STRENGTH.get(dom_code, DEFAULT_STRENGTH))

    att_h, def_h, n_h, b_h, f_h = strengths["ekip_lakay"]
    att_a, def_a, n_a, b_a, f_a = strengths["ekip_deyò"]
    clamp = lambda x: max(0.2, min(4.0, x))  # noqa: E731
    lam_h = clamp(euro_lg["gòl_lakay"] * att_h * def_a * (f_h / f_a))
    lam_a = clamp(euro_lg["gòl_deyò"] * att_a * def_h * (f_a / f_h))
    model = poisson_model(lam_h, lam_a)
    model["fòs"] = {"atak_lakay": att_h, "defans_lakay": def_h, "atak_deyò": att_a, "defans_deyò": def_a,
                    "match_itilize": [n_h, n_a], "baz": [b_h, b_a], "fòs_chanpyona": [f_h, f_a]}
    out["modèl"] = model

    # Fas a fas (Ewòp + chanpyona si yo nan menm chanpyona)
    hn, an = out["ekip_lakay"]["non_lokal"], out["ekip_deyò"]["non_lokal"]
    h2h = [m for m in all_euro if {m["home"], m["away"]} == {eh, ea}]
    for ms in results.values():
        h2h += [m for m in ms if hn and an and {m["home"], m["away"]} == {hn, an}]
    h2h.sort(key=lambda m: m["date"])
    out["fas_a_fas"] = [{"dat": m["date"].strftime("%d/%m/%Y"), "lakay": m["home"], "deyò": m["away"],
                         "skò": f"{int(m['hg'])}-{int(m['ag'])}"} for m in reversed(h2h[-6:])]

    sh, sa = out["ekip_lakay"]["rezime_10"], out["ekip_deyò"]["rezime_10"]
    if sh.get("mwayèn_kònè_fè") is not None and sa.get("mwayèn_kònè_pran") is not None:
        ch = (sh["mwayèn_kònè_fè"] + sa["mwayèn_kònè_pran"]) / 2
        ca = (sa["mwayèn_kònè_fè"] + sh["mwayèn_kònè_pran"]) / 2
        out["kònè_atann"] = {"lakay": round(ch, 1), "deyò": round(ca, 1), "total": round(ch + ca, 1),
                             "mwayèn_chanpyona": None, "nòt": "Baze sou match chanpyona lokal yo sèlman"}

    out["konbine"] = {"metòd": "Modèl Poisson (ajiste pou nivo chanpyona chak ekip). Pa gen kòt mache nan done gratis yo.",
                      "lakay_genyen": model["lakay_genyen"], "nil": model["nil"], "deyò_genyen": model["deyò_genyen"]}

    # Blesi otomatik (API-Football sèlman)
    key = load_env().get("APIFOOTBALL_KEY")
    if fixture and key and fixture.get("source") == "API-Football" and fixture.get("id") and INJURY_BUDGET["rès"] > 0:
        INJURY_BUDGET["rès"] -= 1
        try:
            import fetch_europe
            data = fetch_europe.get_json(f"https://v3.football.api-sports.io/injuries?fixture={fixture['id']}",
                                         {"x-apisports-key": key})
            out["blesi_api"] = [{"ekip": r["team"]["name"], "jwè": r["player"]["name"],
                                 "tip": r["player"].get("type"), "rezon": r["player"].get("reason")}
                                for r in data.get("response", [])]
        except Exception as e:  # noqa: BLE001
            out["blesi_api_erè"] = str(e)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    slug = f"{comp_code.lower()}-{slugify(eh)}-vs-{slugify(ea)}"
    out["slug"] = slug
    path = ANALYSIS_DIR / f"{slug}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, path


def print_summary(a, path):
    h, w = a["ekip_lakay"], a["ekip_deyò"]
    c = a["konbine"]
    print(f"\n{a['lakay']} vs {a['deyò']} — {a['chanpyona']['non']}")
    if "match" in a:
        lè = a['match']['lè_uk']
        print(f"Dat: {a['match']['dat']} {lè}" + ("" if "UTC" in lè else " (lè UK)"))
    for t in (h, w):
        k = t["klasman"] or {}
        r = t["rezime_10"]
        print(f"  {t['non']}: {k.get('pozisyon', '?')}yèm, fòm {r.get('fòm')} | gòl {r.get('mwayèn_gòl_make')}/{r.get('mwayèn_gòl_pran')} "
              f"| kònè {r.get('mwayèn_kònè_fè')} | atak {t['nivo_atak']}, defans {t['nivo_defans']}")
    print(f"  Chans: {a['lakay']} {c['lakay_genyen']}% | Nil {c['nil']}% | {a['deyò']} {c['deyò_genyen']}%  ({c['metòd']})")
    print(f"  Plis 2.5 gòl: {a['modèl']['plis_2_5']}% | Tou de make: {a['modèl']['tou_de_make']}%")
    print(f"\nAnaliz la anrejistre nan: {path}")


def main():
    ap = argparse.ArgumentParser(description="Analize yon match foutbòl")
    ap.add_argument("home", nargs="?", help="Ekip lakay")
    ap.add_argument("away", nargs="?", help="Ekip deyò")
    ap.add_argument("--list-teams", action="store_true", help="Montre non tout ekip yo")
    ap.add_argument("--fixtures", action="store_true", help="Montre match k ap vini yo")
    ap.add_argument("--europe", choices=list(EURO_COMPS), help="CL = Champions League, EL = Europa League")
    args = ap.parse_args()

    if args.list_teams:
        teams = all_teams(load_results())
        for code, info in ALL_DOMESTIC.items():
            names = sorted(t for t, c in teams.items() if c == code)
            print(f"\n{info['non']} ({info['peyi']}):\n  " + ", ".join(names))
        for code, comp in EURO_COMPS.items():
            done, up = load_euro(code)
            names = sorted({m["home"] for m in done + up} | {m["away"] for m in done + up})
            if names:
                print(f"\n{comp['non']}:\n  " + ", ".join(names))
        return
    if args.fixtures:
        fx = load_fixtures()
        if not fx:
            print("Pa gen match k ap vini nan fixtures.csv. Lanse: python3 scripts/fetch_data.py")
        for f in fx:
            print(f"{f['date'].strftime('%d/%m')} {f['time']:>5}  [{ALL_DOMESTIC[f['div']]['non']}]  {f['home']} vs {f['away']}")
        for code, comp in EURO_COMPS.items():
            _, up = load_euro(code)
            for f in up[:40]:
                print(f"{f['date'].strftime('%d/%m')} {f['time']:>5}  [{comp['non']}]  {f['home']} vs {f['away']}  (lè UTC)")
        return
    if not (args.home and args.away):
        ap.error("Bay non 2 ekip yo, pa egzanp: \"Arsenal\" \"Chelsea\"")
    a, path = analyze_europe(args.home, args.away, args.europe) if args.europe else analyze(args.home, args.away)
    print_summary(a, path)


if __name__ == "__main__":
    main()
