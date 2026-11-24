"""Modèl Dixon-Coles + mache parayj yo + motè rekòmandasyon.

- Fòs atak/defans chak ekip, ak match resan yo ki gen plis pwa (time decay)
- Gòl "efikas": melanj gòl reyèl + xG (oswa chout kadre) pou mwens chans/malchans
- Koreksyon Dixon-Coles pou ti skò yo (0-0, 1-0, 0-1, 1-1)
- Menm metòd la pou kònè yo
"""
import json
import math

from config import DATA_DIR

XI = 0.0019          # vitès match yo pèdi pwa (pa jou): ~6 mwa = mwatye pwa
PRIOR = 3.0          # match imajinè "mwayen" pou estabilize ekip ki gen mwens done
MAX_G = 10
BACKTEST_PATH = DATA_DIR / "backtest.json"


# ---------- Fitting ----------

def _weights(matches, ref_date):
    return [math.exp(-XI * max(0, (ref_date - m["date"]).days)) for m in matches]


def sot_factor(matches):
    g = sum(m["hg"] + m["ag"] for m in matches if m.get("hst") is not None and m.get("ast") is not None)
    s = sum(m["hst"] + m["ast"] for m in matches if m.get("hst") is not None and m.get("ast") is not None)
    return g / s if s else None


def effective_goals(m, k):
    """Gòl reyèl melanje ak xG oswa chout kadre (pi estab pou predi)."""
    hg, ag = m["hg"], m["ag"]
    if m.get("hxg") is not None and m.get("axg") is not None:
        return 0.5 * hg + 0.5 * m["hxg"], 0.5 * ag + 0.5 * m["axg"]
    if k and m.get("hst") is not None and m.get("ast") is not None:
        return 0.65 * hg + 0.35 * k * m["hst"], 0.65 * ag + 0.35 * k * m["ast"]
    return hg, ag


def fit_strengths(matches, ref_date, value_fn, iters=40):
    """Metòd iteratif (Maher) pou atak, defans ak avantaj lakay. value_fn(m) -> (lakay, deyò) oswa None."""
    data = []
    for m, w in zip(matches, _weights(matches, ref_date)):
        if m["date"] >= ref_date:
            continue
        v = value_fn(m)
        if v is None or v[0] is None or v[1] is None:
            continue
        data.append((m["home"], m["away"], v[0], v[1], w))
    if len(data) < 20:
        return None
    teams = sorted({d[0] for d in data} | {d[1] for d in data})
    sw = sum(d[4] for d in data)
    avg_h = sum(d[2] * d[4] for d in data) / sw
    avg_a = sum(d[3] * d[4] for d in data) / sw
    base = (avg_h + avg_a) / 2
    att = {t: 1.0 for t in teams}
    dfn = {t: 1.0 for t in teams}
    home = avg_h / avg_a if avg_a else 1.2
    for _ in range(iters):
        num = {t: PRIOR * base for t in teams}
        den = {t: PRIOR * base for t in teams}
        for h, a, x, y, w in data:
            num[h] += w * x
            den[h] += w * home * dfn[a] * base
            num[a] += w * y
            den[a] += w * dfn[h] * base
        att = {t: num[t] / den[t] for t in teams}
        num = {t: PRIOR * base for t in teams}
        den = {t: PRIOR * base for t in teams}
        for h, a, x, y, w in data:
            num[h] += w * y
            den[h] += w * att[a] * base
            num[a] += w * x
            den[a] += w * home * att[h] * base
        dfn = {t: num[t] / den[t] for t in teams}
        ma = sum(att.values()) / len(att)
        md = sum(dfn.values()) / len(dfn)
        att = {t: v / ma for t, v in att.items()}
        dfn = {t: v / md for t, v in dfn.items()}
        hn = sum(w * x for _, _, x, _, w in data)
        hd = sum(w * att[h] * dfn[a] * base for h, a, _, _, w in data)
        home = hn / hd if hd else home
    n_games = {t: 0 for t in teams}
    for h, a, *_ in data:
        n_games[h] += 1
        n_games[a] += 1
    return {"att": att, "def": dfn, "home": home, "base": base, "n": n_games, "data": data}


def tau(x, y, lam, mu, rho):
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    if x == 0 and y == 1:
        return 1 + lam * rho
    if x == 1 and y == 0:
        return 1 + mu * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def fit_rho(fit, real_matches, ref_date):
    """Chèche pi bon rho Dixon-Coles la sou skò reyèl yo."""
    best, best_ll = 0.0, -1e18
    rows = []
    for m, w in zip(real_matches, _weights(real_matches, ref_date)):
        if m["date"] >= ref_date or m["home"] not in fit["att"] or m["away"] not in fit["att"]:
            continue
        if m["hg"] > 1 or m["ag"] > 1:
            continue
        lam, mu = expected(fit, m["home"], m["away"])
        rows.append((int(m["hg"]), int(m["ag"]), lam, mu, w))
    for i in range(-25, 11):
        rho = i / 100
        ll = 0.0
        ok = True
        for x, y, lam, mu, w in rows:
            t = tau(x, y, lam, mu, rho)
            if t <= 0:
                ok = False
                break
            ll += w * math.log(t)
        if ok and ll > best_ll:
            best, best_ll = rho, ll
    return best


def expected(fit, home, away):
    b = fit["base"]
    return (fit["home"] * fit["att"][home] * fit["def"][away] * b,
            fit["att"][away] * fit["def"][home] * b)


def fit_league(matches, ref_date):
    """Fit konplè pou yon chanpyona: gòl (efikas), rho, ak kònè."""
    past = [m for m in matches if m["date"] < ref_date]
    k = sot_factor(past)
    goals = fit_strengths(past, ref_date, lambda m: effective_goals(m, k))
    if not goals:
        return None
    goals["rho"] = fit_rho(goals, past, ref_date)
    corners = fit_strengths(past, ref_date, lambda m: (m.get("hc"), m.get("ac")))
    return {"goals": goals, "corners": corners}


# ---------- Pwobabilite ----------

def pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def score_matrix(lam, mu, rho=0.0):
    grid = [[pmf(i, lam) * pmf(j, mu) * tau(i, j, lam, mu, rho) for j in range(MAX_G + 1)] for i in range(MAX_G + 1)]
    s = sum(map(sum, grid))
    return [[v / s for v in row] for row in grid]


def markets(lam, mu, rho=0.0, corners=None):
    g = score_matrix(lam, mu, rho)
    R = range(MAX_G + 1)

    def p(cond):
        return sum(g[i][j] for i in R for j in R if cond(i, j))

    home, draw = p(lambda i, j: i > j), p(lambda i, j: i == j)
    away = 1 - home - draw
    mk = {
        "1": home, "X": draw, "2": away,
        "1X": home + draw, "X2": draw + away, "12": home + away,
        "DNB1": home / (home + away), "DNB2": away / (home + away),
        "BTTS": p(lambda i, j: i > 0 and j > 0),
        "BTTS_NO": p(lambda i, j: i == 0 or j == 0),
        "H_O0.5": p(lambda i, j: i >= 1), "H_O1.5": p(lambda i, j: i >= 2),
        "A_O0.5": p(lambda i, j: j >= 1), "A_O1.5": p(lambda i, j: j >= 2),
        "AH1-1.5": p(lambda i, j: i - j >= 2), "AH2-1.5": p(lambda i, j: j - i >= 2),
    }
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        mk[f"O{line}"] = p(lambda i, j, L=line: i + j > L)
        mk[f"U{line}"] = 1 - mk[f"O{line}"]
    if corners:
        cl, cm = corners
        tot = cl + cm
        for line in (7.5, 8.5, 9.5, 10.5, 11.5):
            over = 1 - sum(pmf(k, tot) for k in range(int(line) + 1))
            mk[f"C_O{line}"] = over
            mk[f"C_U{line}"] = 1 - over
    scores = sorted(((f"{i}-{j}", g[i][j]) for i in range(6) for j in range(6)), key=lambda x: -x[1])[:6]
    return mk, scores


# ---------- Non mache yo an Kreyòl ----------

def label(key, H, A):
    names = {
        "1": f"{H} genyen", "X": "Match nil", "2": f"{A} genyen",
        "1X": f"{H} oswa nil (1X)", "X2": f"{A} oswa nil (X2)", "12": "Pa gen match nil (12)",
        "DNB1": f"{H} genyen, ranbouse si nil (DNB)", "DNB2": f"{A} genyen, ranbouse si nil (DNB)",
        "BTTS": "Tou de ekip make (Wi)", "BTTS_NO": "Tou de ekip make (Non)",
        "H_O0.5": f"{H} make omwen 1 gòl", "H_O1.5": f"{H} make 2 gòl oswa plis",
        "A_O0.5": f"{A} make omwen 1 gòl", "A_O1.5": f"{A} make 2 gòl oswa plis",
        "AH1-1.5": f"{H} genyen ak 2 gòl diferans oswa plis (-1.5)",
        "AH2-1.5": f"{A} genyen ak 2 gòl diferans oswa plis (-1.5)",
    }
    if key in names:
        return names[key]
    if key.startswith("C_O"):
        return f"Kònè: plis pase {key[3:]}"
    if key.startswith("C_U"):
        return f"Kònè: mwens pase {key[3:]}"
    if key.startswith("O"):
        return f"Plis pase {key[1:]} gòl (Over {key[1:]})"
    if key.startswith("U"):
        return f"Mwens pase {key[1:]} gòl (Under {key[1:]})"
    return key


def family(key):
    if key in ("1", "2", "X", "1X", "X2", "12", "DNB1", "DNB2", "AH1-1.5", "AH2-1.5"):
        return "rezilta"
    if key.startswith("BTTS"):
        return "btts"
    if key.startswith("C_"):
        return "kònè"
    if key.startswith(("H_", "A_")):
        return "gòl_ekip"
    if key.startswith("O"):
        return "over"
    return "under"


# ---------- Backtest (rezilta tès yo) ----------

def load_backtest():
    try:
        return json.loads(BACKTEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def calibration_note(bt, key, prob):
    """'Nan tès la: lè modèl la te di 70-80%, sa te pase 74% (N=210)'"""
    cal = (bt.get("kalibrasyon") or {}).get(key)
    if not cal:
        return None
    b = min(9, int(prob * 10))
    cell = cal.get(str(b))
    if not cell or cell["n"] < 25:
        return None
    return {"bann": f"{b * 10}-{b * 10 + 10}%", "reyisi": round(100 * cell["hit"] / cell["n"]), "n": cell["n"]}


# ---------- Rekòmandasyon (tankou yon parieur pro) ----------

PICK_KEYS = ["O1.5", "O2.5", "U2.5", "U3.5", "BTTS", "BTTS_NO", "1X", "X2", "12", "1", "2",
             "DNB1", "DNB2", "H_O0.5", "A_O0.5", "H_O1.5", "A_O1.5", "AH1-1.5", "AH2-1.5",
             "C_O8.5", "C_O9.5", "C_U10.5", "C_U11.5"]


def recommend(mk, H, A, n_min, market_odds=None, bt=None, disagree=0.0):
    """Retounen chwa ki pi solid yo, ak value bets si gen kòt."""
    bt = bt or {}
    cands = []
    for k in PICK_KEYS:
        if k not in mk:
            continue
        p = mk[k]
        if 0.58 <= p <= 0.88:  # pi wo pase 88%: kòt twò ba, pa vo lapenn
            cands.append((p, k))
    cands.sort(reverse=True)
    picks, fams = [], set()
    for p, k in cands:
        f = family(k)
        if f in fams:
            continue
        note = calibration_note(bt, k, p)
        if note and note["reyisi"] < 58:
            continue  # nan tès la, mache sa a pa t reyisi ase: nou sote l
        fams.add(f)
        stars = 3 if p >= 0.78 else (2 if p >= 0.68 else 1)
        if note and note["reyisi"] < 100 * p - 8:
            stars -= 1  # modèl la twò optimis pou mache sa a
        if n_min < 8:
            stars -= 1
        if family(k) == "rezilta" and disagree > 0.10:
            stars -= 1
        picks.append({
            "mache": k, "non": label(k, H, A), "pousantaj": round(100 * p, 1),
            "kòt_jis": round(1 / p, 2), "etwal": max(1, stars),
            "tès": note,
        })
        if len(picks) == 3:
            break

    values = []
    for k, odds in (market_odds or {}).items():
        if not odds or k not in mk:
            continue
        edge = mk[k] * odds - 1
        if edge >= 0.04 and mk[k] >= 0.30:
            values.append({"mache": k, "non": label(k, H, A), "pousantaj": round(100 * mk[k], 1),
                           "kòt": odds, "kòt_jis": round(1 / mk[k], 2), "avantaj": round(100 * edge, 1)})
    values.sort(key=lambda v: -v["avantaj"])
    return picks, values[:3]


def all_markets_table(mk, H, A):
    order = ["1", "X", "2", "1X", "X2", "12", "DNB1", "DNB2",
             "O0.5", "O1.5", "O2.5", "O3.5", "O4.5", "U1.5", "U2.5", "U3.5",
             "BTTS", "BTTS_NO", "H_O0.5", "H_O1.5", "A_O0.5", "A_O1.5", "AH1-1.5", "AH2-1.5",
             "C_O7.5", "C_O8.5", "C_O9.5", "C_O10.5", "C_O11.5", "C_U8.5", "C_U9.5", "C_U10.5"]
    return [{"mache": k, "non": label(k, H, A), "fanmi": family(k), "pousantaj": round(100 * mk[k], 1),
             "kòt_jis": round(1 / mk[k], 2) if mk[k] > 0.001 else None} for k in order if k in mk]
