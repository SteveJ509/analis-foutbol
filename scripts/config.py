"""Konfigirasyon pwojè a: chanpyona yo, sezon yo ak dosye yo."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
ANALYSIS_DIR = DATA_DIR / "analysis"
CONTEXT_DIR = DATA_DIR / "context"
REPORTS_DIR = ROOT / "reports"

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"

# 5 gran chanpyona yo (kòd football-data.co.uk)
LEAGUES = {
    "E0": {"non": "Premier League", "peyi": "Angletè"},
    "SP1": {"non": "La Liga", "peyi": "Espay"},
    "D1": {"non": "Bundesliga", "peyi": "Almay"},
    "F1": {"non": "Ligue 1", "peyi": "Lafrans"},
    "I1": {"non": "Serie A", "peyi": "Itali"},
}

# Lòt chanpyona: yo sèvi pou fòm ekip ki jwe Champions League / Europa League
EXTRA_LEAGUES = {
    "P1": {"non": "Primeira Liga", "peyi": "Pòtigal"},
    "N1": {"non": "Eredivisie", "peyi": "Olann"},
    "B1": {"non": "Pro League", "peyi": "Bèljik"},
    "T1": {"non": "Süper Lig", "peyi": "Tiki"},
    "SC0": {"non": "Premiership", "peyi": "Ekos"},
    "G1": {"non": "Super League", "peyi": "Grès"},
}
ALL_DOMESTIC = {**LEAGUES, **EXTRA_LEAGUES}

# Fòs apwoksimatif chak chanpyona pou konpare ekip ki soti nan peyi diferan
LEAGUE_STRENGTH = {
    "E0": 1.00, "SP1": 0.97, "I1": 0.95, "D1": 0.94, "F1": 0.88,
    "P1": 0.80, "N1": 0.80, "B1": 0.72, "T1": 0.72, "SC0": 0.66, "G1": 0.66,
}
DEFAULT_STRENGTH = 0.62  # ekip ki soti nan yon chanpyona nou pa genyen

# Koup Ewòp yo
EURO_COMPS = {
    "CL": {"non": "Champions League", "peyi": "Ewòp", "fdorg": "CL", "apifootball": 2},
    "EL": {"non": "Europa League", "peyi": "Ewòp", "fdorg": None, "apifootball": 3},
}


def load_env():
    """Li kle API yo nan fichye .env la (si l egziste)."""
    import os
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env

# Non moun konn ekri -> non ki nan fichye CSV yo
ALIASES = {
    "manchester united": "Man United",
    "man utd": "Man United",
    "manchester city": "Man City",
    "tottenham hotspur": "Tottenham",
    "spurs": "Tottenham",
    "newcastle united": "Newcastle",
    "wolverhampton": "Wolves",
    "nottingham forest": "Nott'm Forest",
    "west ham united": "West Ham",
    "brighton & hove albion": "Brighton",
    "atletico madrid": "Ath Madrid",
    "atlético madrid": "Ath Madrid",
    "athletic bilbao": "Ath Bilbao",
    "athletic club": "Ath Bilbao",
    "real betis": "Betis",
    "real sociedad": "Sociedad",
    "celta vigo": "Celta",
    "bayern munich": "Bayern Munich",
    "bayern münchen": "Bayern Munich",
    "borussia dortmund": "Dortmund",
    "bvb": "Dortmund",
    "borussia monchengladbach": "M'gladbach",
    "gladbach": "M'gladbach",
    "bayer leverkusen": "Leverkusen",
    "eintracht frankfurt": "Ein Frankfurt",
    "rb leipzig": "RB Leipzig",
    "paris saint-germain": "Paris SG",
    "paris saint germain": "Paris SG",
    "psg": "Paris SG",
    "olympique marseille": "Marseille",
    "om": "Marseille",
    "olympique lyon": "Lyon",
    "ol": "Lyon",
    "as monaco": "Monaco",
    "inter milan": "Inter",
    "internazionale": "Inter",
    "ac milan": "Milan",
    "as roma": "Roma",
    "ss lazio": "Lazio",
    "juventus fc": "Juventus",
    "ssc napoli": "Napoli",
    # Non football-data.org ak API-Football itilize pou koup Ewòp yo
    "arsenal fc": "Arsenal",
    "chelsea fc": "Chelsea",
    "liverpool fc": "Liverpool",
    "manchester city fc": "Man City",
    "manchester united fc": "Man United",
    "tottenham hotspur fc": "Tottenham",
    "newcastle united fc": "Newcastle",
    "aston villa fc": "Aston Villa",
    "nottingham forest fc": "Nott'm Forest",
    "real madrid cf": "Real Madrid",
    "fc barcelona": "Barcelona",
    "club atletico de madrid": "Ath Madrid",
    "atletico de madrid": "Ath Madrid",
    "villarreal cf": "Villarreal",
    "real betis balompie": "Betis",
    "fc bayern munchen": "Bayern Munich",
    "bayern munchen": "Bayern Munich",
    "bayer 04 leverkusen": "Leverkusen",
    "vfb stuttgart": "Stuttgart",
    "tsg 1899 hoffenheim": "Hoffenheim",
    "borussia monchengladbach": "M'gladbach",
    "paris saint-germain fc": "Paris SG",
    "olympique de marseille": "Marseille",
    "olympique lyonnais": "Lyon",
    "as monaco fc": "Monaco",
    "lille osc": "Lille",
    "ogc nice": "Nice",
    "stade brestois 29": "Brest",
    "fc internazionale milano": "Inter",
    "juventus fc": "Juventus",
    "atalanta bc": "Atalanta",
    "acf fiorentina": "Fiorentina",
    "bologna fc 1909": "Bologna",
    "sport lisboa e benfica": "Benfica",
    "sl benfica": "Benfica",
    "sporting clube de portugal": "Sp Lisbon",
    "sporting cp": "Sp Lisbon",
    "fc porto": "Porto",
    "sc braga": "Sp Braga",
    "psv": "PSV Eindhoven",
    "psv eindhoven": "PSV Eindhoven",
    "afc ajax": "Ajax",
    "feyenoord rotterdam": "Feyenoord",
    "az alkmaar": "AZ Alkmaar",
    "club brugge kv": "Club Brugge",
    "royale union saint-gilloise": "St. Gilloise",
    "union st. gilloise": "St. Gilloise",
    "celtic fc": "Celtic",
    "rangers fc": "Rangers",
    "galatasaray sk": "Galatasaray",
    "fenerbahce sk": "Fenerbahce",
    "besiktas jk": "Besiktas",
    "olympiacos fc": "Olympiakos",
    "olympiakos piraeus": "Olympiakos",
    "paok fc": "PAOK",
}


def season_code(year_start: int) -> str:
    """2026 -> '2627'"""
    return f"{year_start % 100:02d}{(year_start + 1) % 100:02d}"


def current_season_start(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= 7 else today.year - 1


def seasons_to_load(today: date | None = None) -> list[str]:
    """Sezon kounye a ak sezon anvan an (pou toujou gen 10 match)."""
    start = current_season_start(today)
    return [season_code(start - 1), season_code(start)]
