"""Telechaje done gratis yo sou football-data.co.uk.

Itilizasyon:
    python3 scripts/fetch_data.py
"""
import sys
import time
import urllib.request

from config import ALL_DOMESTIC, BASE_URL, FIXTURES_URL, RAW_DIR, load_env, seasons_to_load

HEADERS = {"User-Agent": "Mozilla/5.0 (analis-foutbol; itilizasyon pèsonèl)"}


def download(url: str, dest) -> bool:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        if len(content) < 50:
            print(f"  ⚠ Fichye a vid: {url}")
            return False
        dest.write_bytes(content)
        print(f"  ✓ {dest.name} ({len(content) // 1024} KB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Pa t ka telechaje {url}: {e}")
        return False


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    total = 0
    for season in seasons_to_load():
        print(f"Sezon {season[:2]}/{season[2:]}:")
        for code, info in ALL_DOMESTIC.items():
            total += 1
            url = BASE_URL.format(season=season, code=code)
            if download(url, RAW_DIR / f"{code}_{season}.csv"):
                ok += 1
            time.sleep(0.5)  # pa twò prese sit la
    print("Match k ap vini (fixtures):")
    total += 1
    if download(FIXTURES_URL, RAW_DIR / "fixtures.csv"):
        ok += 1
    print(f"\nFini: {ok}/{total} fichye telechaje nan {RAW_DIR}")

    env = load_env()
    if env.get("FOOTBALL_DATA_TOKEN") or env.get("APIFOOTBALL_KEY"):
        print("\nKoup Ewòp yo:")
        import fetch_europe
        fetch_europe.main()
    else:
        print("\n(Pou Champions League ak Europa League, mete kle API yo nan .env — gade README.md)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
