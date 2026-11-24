"""Chaje fichye CSV yo epi jwenn match ak ekip yo."""
import csv
import difflib
import json
import unicodedata
from datetime import datetime

from config import ALIASES, ALL_DOMESTIC, RAW_DIR, seasons_to_load


def norm(name):
    """'Bayern München FC' -> 'bayern munchen fc'"""
    name = unicodedata.normalize("NFKD", name or "")
    name = "".join(c for c in name if not unicodedata.combining(c))
    return " ".join(name.lower().replace(".", " ").split())


NORM_ALIASES = {norm(k): v for k, v in ALIASES.items()}
SUFFIXES = {"fc", "cf", "afc", "sc", "sk", "kv", "bc", "ac", "as", "ssc", "ss", "osc", "jk", "cp", "sl", "1909", "1899", "04"}


def strip_suffixes(n):
    return " ".join(w for w in n.split() if w not in SUFFIXES)


def _float(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _date(v):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(v.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _read_csv(path):
    # Fichye yo konn gen BOM oswa karaktè latin-1
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    return []


def _row_to_match(row, season=None):
    d = _date(row.get("Date", ""))
    hg, ag = _float(row.get("FTHG")), _float(row.get("FTAG"))
    if not d or not row.get("HomeTeam") or not row.get("AwayTeam"):
        return None
    return {
        "div": (row.get("Div") or "").strip(),
        "season": season,
        "date": d,
        "time": row.get("Time", ""),
        "home": row["HomeTeam"].strip(),
        "away": row["AwayTeam"].strip(),
        "hg": hg,
        "ag": ag,
        "hs": _float(row.get("HS")), "as": _float(row.get("AS")),
        "hst": _float(row.get("HST")), "ast": _float(row.get("AST")),
        "hc": _float(row.get("HC")), "ac": _float(row.get("AC")),
        "hy": _float(row.get("HY")), "ay": _float(row.get("AY")),
        "hr": _float(row.get("HR")), "ar": _float(row.get("AR")),
        "hxg": _float(row.get("HxG")), "axg": _float(row.get("AxG")),
        "referee": row.get("Referee", ""),
        "odds_h": _float(row.get("AvgH") or row.get("B365H") or row.get("PSH")),
        "odds_d": _float(row.get("AvgD") or row.get("B365D") or row.get("PSD")),
        "odds_a": _float(row.get("AvgA") or row.get("B365A") or row.get("PSA")),
        "odds_o25": _float(row.get("Avg>2.5") or row.get("B365>2.5")),
        "odds_u25": _float(row.get("Avg<2.5") or row.get("B365<2.5")),
        # Pi bon kòt sou mache a (pou chèche value)
        "max_h": _float(row.get("MaxH") or row.get("BbMxH")),
        "max_d": _float(row.get("MaxD") or row.get("BbMxD")),
        "max_a": _float(row.get("MaxA") or row.get("BbMxA")),
        "max_o25": _float(row.get("Max>2.5") or row.get("BbMx>2.5")),
        "max_u25": _float(row.get("Max<2.5") or row.get("BbMx<2.5")),
    }


def load_results(league_code=None):
    """Retounen {div: [match...]} pou match ki fin jwe yo, ranje pa dat."""
    out = {}
    codes = [league_code] if league_code else list(ALL_DOMESTIC)
    for code in codes:
        matches = []
        for season in seasons_to_load():
            path = RAW_DIR / f"{code}_{season}.csv"
            if not path.exists():
                continue
            for row in _read_csv(path):
                m = _row_to_match(row, season)
                if m and m["hg"] is not None and m["ag"] is not None:
                    m["div"] = m["div"] or code
                    matches.append(m)
        matches.sort(key=lambda m: m["date"])
        out[code] = matches
    return out


def load_fixtures():
    path = RAW_DIR / "fixtures.csv"
    if not path.exists():
        return []
    fixtures = []
    for row in _read_csv(path):
        m = _row_to_match(row)
        if m and m["div"] in ALL_DOMESTIC:
            fixtures.append(m)
    fixtures.sort(key=lambda m: m["date"])
    return fixtures


def all_teams(results):
    teams = {}
    for code, matches in results.items():
        current = max((m["season"] for m in matches), default=None)
        for m in matches:
            if m["season"] == current:
                teams[m["home"]] = code
                teams[m["away"]] = code
    return teams  # {non ekip: kòd chanpyona}


def resolve_team(name, teams, cutoff=0.55):
    """Jwenn non egzak ekip la nan done yo, menm si moun nan ekri l yon lòt jan."""
    if not name:
        return None
    if name in teams:
        return name
    low = norm(name)
    if low in NORM_ALIASES and NORM_ALIASES[low] in teams:
        return NORM_ALIASES[low]
    by_norm = {norm(t): t for t in teams}
    if low in by_norm:
        return by_norm[low]
    short = strip_suffixes(low)
    by_short = {strip_suffixes(k): t for k, t in by_norm.items()}
    if short in by_short:
        return by_short[short]
    contains = [t for k, t in by_short.items() if k and (short in k or k in short)]
    if len(contains) == 1:
        return contains[0]
    close = difflib.get_close_matches(short, list(by_short), n=1, cutoff=cutoff)
    if close:
        return by_short[close[0]]
    return None


# ---------- Koup Ewòp ----------

def load_euro(code):
    """Retounen (match fini yo, match k ap vini yo) pou CL oswa EL."""
    path = RAW_DIR / f"euro_{code}.json"
    if not path.exists():
        return [], []
    done, upcoming = [], []
    for r in json.loads(path.read_text(encoding="utf-8")):
        try:
            d = datetime.fromisoformat(r["dat"].replace("Z", "+00:00")).replace(tzinfo=None)
        except (KeyError, ValueError, AttributeError):
            continue
        m = {
            "div": code, "season": "euro", "date": d, "time": d.strftime("%H:%M"),
            "home": r.get("lakay"), "away": r.get("deyò"),
            "hg": r.get("gòl_lakay"), "ag": r.get("gòl_deyò"),
            "stage": r.get("etap") or "", "venue": r.get("estad"), "city": r.get("vil"),
            "id": r.get("id"), "source": r.get("sous"), "referee": "",
        }
        for k in ("hs", "as", "hst", "ast", "hc", "ac", "hy", "ay", "hr", "ar", "hxg", "axg"):
            m[k] = None
        if not m["home"] or not m["away"]:
            continue
        (done if r.get("fini") and m["hg"] is not None else upcoming).append(m)
    done.sort(key=lambda m: m["date"])
    upcoming.sort(key=lambda m: m["date"])
    return done, upcoming
