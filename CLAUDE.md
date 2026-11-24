# Analis Foutbòl

Pwojè pou analize match nan 5 gran chanpyona Ewòp yo, Champions League ak Europa League. Pale ak itilizatè a an **Kreyòl ayisyen**.

- Done estatistik: football-data.co.uk (gratis, pa bezwen kle). Script: `scripts/fetch_data.py`
- Koup Ewòp: `scripts/fetch_europe.py` (football-data.org pou CL, API-Football pou EL; kle yo nan `.env`)
- Analiz: `scripts/analyze_match.py` (`--europe CL` oswa `--europe EL` pou koup yo) (fòm, atak, defans, kònè, klasman, modèl Poisson, kòt mache)
- Kontèks (blesi, estad, move tan, enpòtans): ajan `analis-foutbol` la chèche yo sou entènèt
- Rapò HTML pou telefòn: `scripts/build_report.py` → `reports/`
- Sit live: `scripts/build_site.py` → `site/`, pibliye pa `.github/workflows/sit.yml` (GitHub Actions, 2 fwa pa jou)
- Kontèks ajan an ekri nan `data/context/` itilize pa sit la tou: commit epi push yo.

Lè itilizatè a mande analiz yon match, sèvi ak ajan `analis-foutbol` la (oswa kòmand `/analiz`).
Python itilize sèlman bibliyotèk estanda yo. Pa ajoute depandans san rezon.
