"""Sove prediksyon yo anvan match yo, epi konpare yo ak rezilta reyèl yo apre.

- data/predictions/<dat>-<slug>.json : analiz la jan l te ye anvan match la kòmanse (li bloke apre sa)
- Rezilta yo soti nan football-data.co.uk (ak kònè), football-data.org, oswa done Ewòp yo.
"""
import json
from datetime import datetime, timedelta, timezone

from backtest import outcome
from config import DATA_DIR, EURO_COMPS, RAW_DIR
from footdata import all_teams, load_euro, load_results, resolve_team

PRED_DIR = DATA_DIR / "predictions"


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def kickoff(when, time_label):
    """Dat + lè match la (UTC apeprè)."""
    try:
        hh, mm = time_label.split()[0].split(":")
        return when.replace(hour=int(hh), minute=int(mm))
    except (ValueError, AttributeError, IndexError):
        return when.replace(hour=12, minute=0)


def save_snapshot(a, ko, code):
    """Sove prediksyon an. Apre match la kòmanse, nou pa janm chanje l ankò."""
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    path = PRED_DIR / f"{ko:%Y%m%d}-{a['slug']}.json"
    if path.exists():
        if _now() >= ko:
            return path  # bloke: match la kòmanse
        try:  # pa reekri fichye a si prediksyon yo pa chanje (pou depo a pa grosi pou anyen)
            old = json.loads(path.read_text(encoding="utf-8"))["analiz"]
            keys = ("rekòmandasyon", "konbine", "tout_mache")
            if all(old.get(k) == a.get(k) for k in keys):
                return path
        except (ValueError, KeyError):
            pass
    data = {"kickoff": ko.strftime("%Y-%m-%dT%H:%M"), "kòd": code, "analiz": a}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class Results:
    """Tout rezilta nou konnen, pou jwenn skò yon match fasil."""

    def __init__(self):
        self.domestic = load_results()
        self.teams = all_teams(self.domestic)
        self.recent = []
        p = RAW_DIR / "recent_domestic.json"
        if p.exists():
            try:
                self.recent = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                self.recent = []
        self.euro = {c: load_euro(c)[0] for c in EURO_COMPS}

    def find(self, code, home, away, ko):
        lo, hi = ko - timedelta(days=1, hours=12), ko + timedelta(days=1, hours=12)
        # 1) CSV (gen kònè)
        for m in self.domestic.get(code, []):
            if m["home"] == home and m["away"] == away and lo <= m["date"] <= hi:
                return {"hg": int(m["hg"]), "ag": int(m["ag"]), "hc": m.get("hc"), "ac": m.get("ac"), "sous": "football-data.co.uk"}
        # 2) Koup Ewòp
        for m in self.euro.get(code, []):
            if m["home"] == home and m["away"] == away and lo <= m["date"] <= hi:
                return {"hg": int(m["hg"]), "ag": int(m["ag"]), "hc": None, "ac": None, "sous": m.get("source")}
        # 3) football-data.org (rezilta rapid, san kònè)
        div_teams = {t: c for t, c in self.teams.items() if c == code}
        for r in self.recent:
            if r.get("div") != code or r.get("gòl_lakay") is None:
                continue
            try:
                d = datetime.fromisoformat(r["dat"].replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
            except (KeyError, ValueError):
                continue
            if not (lo <= d <= hi):
                continue
            if resolve_team(r["lakay"], div_teams, 0.75) == home and resolve_team(r["deyò"], div_teams, 0.75) == away:
                return {"hg": int(r["gòl_lakay"]), "ag": int(r["gòl_deyò"]), "hc": None, "ac": None, "sous": "football-data.org"}
        return None


def evaluate(a, res):
    """Pou chak prediksyon: ✅, ❌ oswa ⏳ (lè nou poko gen done kònè)."""
    rec = a.get("rekòmandasyon") or {}
    rows = []
    for kind, items in (("Chwa", rec.get("chwa") or []), ("Value", rec.get("value") or [])):
        for p in items:
            o = outcome(p["mache"], res["hg"], res["ag"], res["hc"], res["ac"])
            rows.append({"tip": kind, "mache": p["mache"], "non": p["non"], "pousantaj": p["pousantaj"],
                         "etwal": p.get("etwal"), "rezilta": "⏳" if o is None else ("✅" if o else "❌")})
    # Pi gwo chans 1X2 la
    c = a.get("konbine") or {}
    if c:
        trio = [("1", c.get("lakay_genyen", 0), f"{a['lakay']} genyen"), ("X", c.get("nil", 0), "Match nil"),
                ("2", c.get("deyò_genyen", 0), f"{a['deyò']} genyen")]
        k, p, name = max(trio, key=lambda x: x[1])
        o = outcome(k, res["hg"], res["ag"], None, None)
        rows.append({"tip": "1X2", "mache": k, "non": name, "pousantaj": p, "rezilta": "✅" if o else "❌"})
    return rows


def collect(days=14):
    """Tout prediksyon ki fini nan dènye jou yo, ak rezilta yo."""
    if not PRED_DIR.exists():
        return [], {"chwa": [0, 0], "1x2": [0, 0]}
    R = Results()
    now = _now()
    out = []
    tally = {"chwa": [0, 0], "1x2": [0, 0]}
    for path in sorted(PRED_DIR.glob("*.json")):
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
            ko = datetime.strptime(snap["kickoff"], "%Y-%m-%dT%H:%M")
        except (ValueError, KeyError):
            continue
        if ko > now - timedelta(hours=2):
            continue  # match la poko fini
        a = snap["analiz"]
        res = R.find(snap["kòd"], a["lakay"], a["deyò"], ko)
        if not res:
            continue
        rows = evaluate(a, res)
        for r in rows:
            key = "1x2" if r["tip"] == "1X2" else ("chwa" if r["tip"] == "Chwa" else None)
            if key and r["rezilta"] in ("✅", "❌"):
                tally[key][0] += 1
                tally[key][1] += int(r["rezilta"] == "✅")
        if ko >= now - timedelta(days=days):
            out.append({"kickoff": ko, "kòd": snap["kòd"], "analiz": a, "rezilta": res, "prediksyon": rows})
    out.sort(key=lambda x: x["kickoff"], reverse=True)
    return out, tally
