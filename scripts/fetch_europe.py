"""Telechaje match Champions League ak Europa League.

Sous yo (tou de gratis, men yo mande yon kle):
  - football-data.org  -> Champions League    (kle: FOOTBALL_DATA_TOKEN)
  - API-Football        -> Champions League + Europa League (kle: APIFOOTBALL_KEY)

Mete kle yo nan fichye .env la (gade .env.example).

Itilizasyon:
    python3 scripts/fetch_europe.py
"""
import json
import sys
import urllib.error
import urllib.request

from config import EURO_COMPS, RAW_DIR, current_season_start, load_env


def get_json(url, headers):
    req = urllib.request.Request(url, headers={"User-Agent": "analis-foutbol", **headers})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def from_football_data_org(code, season, token):
    url = f"https://api.football-data.org/v4/competitions/{code}/matches?season={season}"
    data = get_json(url, {"X-Auth-Token": token})
    out = []
    for m in data.get("matches", []):
        score = m.get("score", {})
        # regularTime = 90 minit (si match la te ale nan pwolongasyon)
        reg = score.get("regularTime") or score.get("fullTime") or {}
        finished = m.get("status") == "FINISHED"
        out.append({
            "id": m.get("id"),
            "dat": m.get("utcDate"),
            "etap": m.get("stage"),
            "lakay": (m.get("homeTeam") or {}).get("name"),
            "deyò": (m.get("awayTeam") or {}).get("name"),
            "gòl_lakay": reg.get("home") if finished else None,
            "gòl_deyò": reg.get("away") if finished else None,
            "fini": finished,
            "estad": m.get("venue"),
            "vil": None,
            "sous": "football-data.org",
        })
    return out


def from_api_football(league_id, season, key):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    data = get_json(url, {"x-apisports-key": key})
    errors = data.get("errors")
    if errors:
        raise RuntimeError(f"API-Football refize: {errors}")
    out = []
    for r in data.get("response", []):
        fx, teams = r.get("fixture", {}), r.get("teams", {})
        status = (fx.get("status") or {}).get("short")
        finished = status in ("FT", "AET", "PEN")
        ft = (r.get("score") or {}).get("fulltime") or {}  # 90 minit
        venue = fx.get("venue") or {}
        out.append({
            "id": fx.get("id"),
            "dat": fx.get("date"),
            "etap": (r.get("league") or {}).get("round"),
            "lakay": (teams.get("home") or {}).get("name"),
            "deyò": (teams.get("away") or {}).get("name"),
            "gòl_lakay": ft.get("home") if finished else None,
            "gòl_deyò": ft.get("away") if finished else None,
            "fini": finished,
            "estad": venue.get("name"),
            "vil": venue.get("city"),
            "sous": "API-Football",
        })
    return out


# Kòd football-data.org -> kòd football-data.co.uk
DOMESTIC_FDORG = {"PL": "E0", "PD": "SP1", "BL1": "D1", "FL1": "F1", "SA": "I1"}


def fetch_domestic_upcoming(token, days=10):
    """Kalandriye match chanpyona k ap vini yo (lè fixtures.csv poko gen yo)."""
    import time
    from datetime import date, timedelta
    today = date.today()
    out = []
    for code, div in DOMESTIC_FDORG.items():
        url = (f"https://api.football-data.org/v4/competitions/{code}/matches"
               f"?dateFrom={today}&dateTo={today + timedelta(days=days)}")
        try:
            data = get_json(url, {"X-Auth-Token": token})
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ Kalandriye {code}: {e}")
            continue
        for m in data.get("matches", []):
            if m.get("status") in ("SCHEDULED", "TIMED"):
                out.append({"div": div, "dat": m.get("utcDate"),
                            "lakay": (m.get("homeTeam") or {}).get("name"),
                            "deyò": (m.get("awayTeam") or {}).get("name")})
        time.sleep(7)  # plan gratis la: 10 demann pa minit
    (RAW_DIR / "upcoming_domestic.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  ✓ Kalandriye chanpyona yo: {len(out)} match k ap vini")


# ID chanpyona yo nan API-Football -> kòd football-data.co.uk
DOMESTIC_APIFOOTBALL = {39: "E0", 140: "SP1", 78: "D1", 61: "F1", 135: "I1"}


def fetch_domestic_upcoming_apifootball(key, days=10):
    """Menm bagay ak fetch_domestic_upcoming, men ak API-Football (5 demann)."""
    from datetime import date, timedelta
    today = date.today()
    season = current_season_start()
    out = []
    for league_id, div in DOMESTIC_APIFOOTBALL.items():
        url = (f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
               f"&from={today}&to={today + timedelta(days=days)}")
        try:
            data = get_json(url, {"x-apisports-key": key})
            if data.get("errors"):
                raise RuntimeError(data["errors"])
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ Kalandriye {div}: {e}")
            continue
        for r in data.get("response", []):
            if (r.get("fixture", {}).get("status") or {}).get("short") in ("NS", "TBD"):
                out.append({"div": div, "dat": r["fixture"].get("date"),
                            "lakay": r["teams"]["home"]["name"], "deyò": r["teams"]["away"]["name"]})
    (RAW_DIR / "upcoming_domestic.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  ✓ Kalandriye chanpyona yo (API-Football): {len(out)} match k ap vini")


def main():
    env = load_env()
    token = env.get("FOOTBALL_DATA_TOKEN")
    key = env.get("APIFOOTBALL_KEY")
    season = current_season_start()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not token and not key:
        print("⚠ Pa gen kle API pou koup Ewòp yo. Gade .env.example epi README.md.")
        return 1

    ok = 0
    for code, comp in EURO_COMPS.items():
        matches, errors = None, []
        if token and comp["fdorg"]:
            try:
                matches = from_football_data_org(comp["fdorg"], season, token)
            except Exception as e:  # noqa: BLE001
                errors.append(f"football-data.org: {e}")
        if not matches and key:
            try:
                matches = from_api_football(comp["apifootball"], season, key)
            except Exception as e:  # noqa: BLE001
                errors.append(f"API-Football: {e}")
        if matches:
            (RAW_DIR / f"euro_{code}.json").write_text(json.dumps(matches, ensure_ascii=False, indent=1), encoding="utf-8")
            done = sum(m["fini"] for m in matches)
            print(f"  ✓ {comp['non']}: {done} match fini, {len(matches) - done} k ap vini ({matches[0]['sous']})")
            ok += 1
        else:
            print(f"  ✗ {comp['non']}: pa jwenn done.")
            for err in errors:
                print(f"      {err}")
            if code == "EL" and not key:
                print("      Europa League bezwen yon kle API-Football (APIFOOTBALL_KEY).")
    if token:
        fetch_domestic_upcoming(token)
    elif key:
        fetch_domestic_upcoming_apifootball(key)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
