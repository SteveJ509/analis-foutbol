"""Teste modèl la sou match ki deja jwe, tankou si nou te la anvan match yo.

Pou chak semèn, modèl la aprann SÈLMAN ak match ki te jwe anvan semèn nan,
epi li predi match semèn nan. Apre sa nou konpare ak rezilta reyèl yo.

Itilizasyon:
    python3 scripts/backtest.py
"""
import json
import math
from datetime import timedelta

import combo as C
import model as M
from config import LEAGUES
from footdata import load_results

WARMUP = 120
LAST = {}  # kantite match anvan nou kòmanse teste


def outcome(key, hg, ag, hc, ac):
    hg, ag = int(hg), int(ag)
    t = hg + ag
    simple = {
        "1": hg > ag, "X": hg == ag, "2": ag > hg, "1X": hg >= ag, "X2": ag >= hg, "12": hg != ag,
        "BTTS": hg > 0 and ag > 0, "BTTS_NO": hg == 0 or ag == 0,
        "H_O0.5": hg >= 1, "H_O1.5": hg >= 2, "A_O0.5": ag >= 1, "A_O1.5": ag >= 2,
        "AH1-1.5": hg - ag >= 2, "AH2-1.5": ag - hg >= 2,
    }
    if key in simple:
        return simple[key]
    if key in ("DNB1", "DNB2"):
        return None if hg == ag else (hg > ag if key == "DNB1" else ag > hg)
    if key.startswith("C_"):
        if hc is None or ac is None:
            return None
        line = float(key[3:])
        return (hc + ac > line) if key[2] == "O" else (hc + ac < line)
    if key[0] in "OU":
        line = float(key[1:])
        return t > line if key[0] == "O" else t < line
    return None


def implied3(h, d, a):
    if not (h and d and a):
        return None
    inv = [1 / h, 1 / d, 1 / a]
    s = sum(inv)
    return [x / s for x in inv]


def run():
    cal = {}
    ll = {w: 0.0 for w in range(11)}
    n_ll = 0
    picks = {"tout": [0, 0], "1": [0, 0], "2": [0, 0], "3": [0, 0]}
    value = {"paryaj": 0, "pwofi": 0.0, "genyen": 0}
    per_league = {}
    tested = 0
    weekend = {}  # semèn -> lis (a, dat, rezilta) pou tès konbinezon yo

    for code, info in LEAGUES.items():
        matches = load_results(code).get(code, [])
        if len(matches) < WARMUP + 50:
            print(f"  ⚠ {info['non']}: pa ase done ({len(matches)} match)")
            continue
        test = matches[WARMUP:]
        weeks = {}
        for m in test:
            wk = (m["date"] - timedelta(days=m["date"].weekday())).date()
            weeks.setdefault(wk, []).append(m)
        lg_n = lg_hit = 0
        for wk, games in sorted(weeks.items()):
            ref = games[0]["date"].replace(hour=0) - timedelta(days=games[0]["date"].weekday())
            ref = min(g["date"] for g in games).replace(hour=0, minute=0)
            fit = M.fit_league(matches, ref)
            if not fit:
                continue
            gfit, cfit = fit["goals"], fit["corners"]
            for m in games:
                if m["home"] not in gfit["att"] or m["away"] not in gfit["att"]:
                    continue
                lam, mu = M.expected(gfit, m["home"], m["away"])
                corners = None
                if cfit and m["home"] in cfit["att"] and m["away"] in cfit["att"]:
                    corners = M.expected(cfit, m["home"], m["away"])
                mk, _ = M.markets(lam, mu, gfit["rho"], corners)
                tested += 1
                if m["date"].weekday() in (4, 5, 6, 0):
                    a = {"lakay": m["home"], "deyò": m["away"], "slug": f"{code}-{m['home']}-{m['away']}-{m['date']:%Y%m%d}",
                         "chanpyona": {"non": info["non"]}, "tout_mache": M.all_markets_table(mk, m["home"], m["away"])}
                    wkey = (m["date"] - timedelta(days=(m["date"].weekday() - 4) % 7)).date()
                    weekend.setdefault(wkey, []).append((a, m))

                # Kalibrasyon
                for k, p in mk.items():
                    o = outcome(k, m["hg"], m["ag"], m["hc"], m["ac"])
                    if o is None:
                        continue
                    b = str(min(9, int(p * 10)))
                    cell = cal.setdefault(k, {}).setdefault(b, {"n": 0, "hit": 0, "p": 0.0})
                    cell["n"] += 1
                    cell["hit"] += int(o)
                    cell["p"] += p

                # Modèl kont mache (log loss 1X2) pou chwazi pi bon melanj lan
                imp = implied3(m["odds_h"], m["odds_d"], m["odds_a"])
                res = 0 if m["hg"] > m["ag"] else (1 if m["hg"] == m["ag"] else 2)
                if imp:
                    mp = [mk["1"], mk["X"], mk["2"]]
                    for w in range(11):
                        q = (w / 10) * mp[res] + (1 - w / 10) * imp[res]
                        ll[w] -= math.log(max(q, 1e-9))
                    n_ll += 1

                # Pi bon chwa a (premye rekòmandasyon an)
                n_min = min(gfit["n"].get(m["home"], 0), gfit["n"].get(m["away"], 0))
                top, _ = M.recommend(mk, m["home"], m["away"], n_min)
                if top:
                    o = outcome(top[0]["mache"], m["hg"], m["ag"], m["hc"], m["ac"])
                    if o is not None:
                        for key in ("tout", str(top[0]["etwal"])):
                            picks[key][0] += 1
                            picks[key][1] += int(o)
                        lg_n += 1
                        lg_hit += int(o)

                # Value bets ak pi bon kòt mache a (melanj 50/50)
                if imp:
                    blend = {"1": 0.5 * mk["1"] + 0.5 * imp[0], "X": 0.5 * mk["X"] + 0.5 * imp[1],
                             "2": 0.5 * mk["2"] + 0.5 * imp[2]}
                    for k, odds in (("1", m["max_h"]), ("X", m["max_d"]), ("2", m["max_a"])):
                        if odds and blend[k] * odds - 1 >= 0.04 and blend[k] >= 0.30:
                            won = outcome(k, m["hg"], m["ag"], None, None)
                            value["paryaj"] += 1
                            value["genyen"] += int(won)
                            value["pwofi"] += (odds - 1) if won else -1
        if lg_n:
            per_league[info["non"]] = {"n": lg_n, "reyisi": round(100 * lg_hit / lg_n, 1)}
        print(f"  ✓ {info['non']}: {lg_n} match teste")

    LAST["weekend"] = weekend
    # Tès konbinezon wikenn yo.
    # 1) Sou 60% premye wikenn yo: ki mache ki vrèman pase ≥85% lè modèl la di 85-95%?
    # 2) Sou 40% dènye wikenn yo (done modèl la pa t wè): nou teste konbinezon yo ak mache sa yo sèlman.
    weeks = [w for w in sorted(weekend) if len(weekend[w]) >= 15]
    cut = int(len(weeks) * 0.6)

    def market_table(week_keys):
        tab = {}
        for wk in week_keys:
            for a, m in weekend[wk]:
                for r in a["tout_mache"]:
                    k, p = r["mache"], r["pousantaj"] / 100
                    if k in C.ALLOWED and C.MIN_P <= p <= C.MAX_P:
                        o = outcome(k, m["hg"], m["ag"], m["hc"], m["ac"])
                        if o is None:
                            continue
                        t = tab.setdefault(k, {"n": 0, "hit": 0})
                        t["n"] += 1
                        t["hit"] += int(o)
        return {k: {"n": v["n"], "reyisi": round(100 * v["hit"] / v["n"], 1)} for k, v in tab.items()}

    train_tab = market_table(weeks[:cut])
    combo_res = {t["id"]: {"wikenn": 0, "genyen": 0, "kòt": [], "seleksyon": 0, "seleksyon_genyen": 0} for t in C.TARGETS}
    for wkey in weeks[cut:]:
        items = weekend[wkey]
        combos, _ = C.make_combos([(a, m["date"]) for a, m in items], bt={"konbinezon_mache": train_tab})
        by_slug = {a["slug"]: m for a, m in items}
        for c in combos:
            r = combo_res[c["id"]]
            ok = True
            for leg in c["seleksyon"]:
                m = by_slug[leg["slug"]]
                o = outcome(leg["mache"], m["hg"], m["ag"], m["hc"], m["ac"])
                r["seleksyon"] += 1
                r["seleksyon_genyen"] += int(bool(o))
                ok = ok and bool(o)
            r["wikenn"] += 1
            r["genyen"] += int(ok)
            r["kòt"].append(c["kòt_total"])
    for r in combo_res.values():
        ks = r.pop("kòt")
        r["kòt_mwayèn"] = round(sum(ks) / len(ks), 2) if ks else None
        r["reyisi"] = round(100 * r["genyen"] / r["wikenn"], 1) if r["wikenn"] else None
        r["seleksyon_reyisi"] = round(100 * r["seleksyon_genyen"] / r["seleksyon"], 1) if r["seleksyon"] else None
    full_tab = market_table(weeks)  # pou sit la: tout wikenn yo

    best_w = min(ll, key=ll.get) / 10 if n_ll else 0.4
    out = {
        "match_teste": tested,
        "pwa_modèl": best_w,
        "log_loss": {"modèl": round(ll[10] / n_ll, 4), "mache": round(ll[0] / n_ll, 4),
                     "melanj": round(ll[int(best_w * 10)] / n_ll, 4)} if n_ll else None,
        "chwa": {k: {"n": v[0], "reyisi": round(100 * v[1] / v[0], 1) if v[0] else None} for k, v in picks.items()},
        "pa_chanpyona": per_league,
        "value": {**value, "pwofi": round(value["pwofi"], 1),
                  "roi": round(100 * value["pwofi"] / value["paryaj"], 1) if value["paryaj"] else None},
        "kalibrasyon": cal,
        "konbinezon": combo_res,
        "konbinezon_mache": full_tab,
    }
    M.BACKTEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    M.BACKTEST_PATH.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"\nMatch teste: {tested}")
    print(f"Pi bon chwa a reyisi: {out['chwa']['tout']['reyisi']}% ({out['chwa']['tout']['n']} chwa)")
    for s in ("3", "2", "1"):
        c = out["chwa"][s]
        if c["n"]:
            print(f"  {'★' * int(s)}: {c['reyisi']}% ({c['n']})")
    if out["log_loss"]:
        print(f"Log loss 1X2 — modèl: {out['log_loss']['modèl']}, mache: {out['log_loss']['mache']}, "
              f"melanj ({int(best_w * 100)}% modèl): {out['log_loss']['melanj']}  (pi ba = pi bon)")
    v = out["value"]
    print(f"Value bets: {v['paryaj']} paryaj, {v['genyen']} genyen, pwofi {v['pwofi']} inite, ROI {v['roi']}%")
    print("Mache pou konbinezon (85-95% dapre modèl la):")
    for k, v in sorted(full_tab.items(), key=lambda x: -x[1]["reyisi"]):
        print(f"  {k:<8} pase {v['reyisi']}% (n={v['n']}) {'✓' if v['n'] >= 30 and v['reyisi'] >= 85 else '✗'}")
    for cid, r in combo_res.items():
        print(f"Konbinezon {cid}: {r['genyen']}/{r['wikenn']} wikenn genyen ({r['reyisi']}%), kòt mwayèn {r['kòt_mwayèn']}, "
              f"seleksyon yo pase {r['seleksyon_reyisi']}%")
    for k in ("O1.5", "O2.5", "BTTS"):
        for b in ("6", "7", "8"):
            c = cal.get(k, {}).get(b)
            if c and c["n"]:
                print(f"  {k} {int(b) * 10}-{int(b) * 10 + 10}%: pase {round(100 * c['hit'] / c['n'])}% (n={c['n']})")
    return out


if __name__ == "__main__":
    run()
