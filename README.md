# ⚽ Analis Foutbòl — Ajan Claude Code

Ajan sa a analize match nan **Premier League, La Liga, Bundesliga, Ligue 1, Serie A, Champions League ak Europa League**, epi li fè yon rapò ou ka ouvri sou telefòn ou.

Men sa ki nan rapò a:
- 10 dènye match chak ekip, ak fòm lakay ak deyò
- Gòl yo make ak gòl yo pran, chout, xG, kat
- Nivo atak ak defans chak ekip
- Kònè (mwayèn ak kònè atann pou match la)
- Plis/mwens 2.5 gòl, tou de ekip make
- Klasman ak fas a fas
- Blesi, suspansyon ak jwè kle ki pap la
- Estad, teren, move tan, abit ak enpòtans match la
- Pousantaj chans pou chak ekip (modèl Poisson + kòt bookmaker yo)

**Done yo gratis.** Pou 5 chanpyona yo, estatistik yo soti sou football-data.co.uk, kote pa gen kle API pou kreye. Pou Champions League ak Europa League, ou bezwen 2 kle gratis (gade seksyon 2). Blesi ak nouvèl yo, se Claude ki chèche yo sou entènèt.

---

## 1. Enstale pwojè a sou Chromebook ou

1. Telechaje `analis-foutbol.zip`.
2. Ouvri aplikasyon **Files**, epi trennen fichye zip la nan **Linux files**.
3. Nan Terminal la:
   ```bash
   unzip analis-foutbol.zip
   cd analis-foutbol
   ```
4. Telechaje done yo:
   ```bash
   python3 scripts/fetch_data.py
   ```
5. Teste l:
   ```bash
   python3 scripts/analyze_match.py --fixtures
   ```
   Kòmand sa a montre match k ap vini yo.

Ou pa bezwen enstale anyen ak `pip`. Pwojè a itilize sèlman sa ki deja vini ak Python.

---

## 2. Champions League ak Europa League

Sit football-data.co.uk pa gen koup Ewòp yo. **Yon sèl kle API-Football ase** pou Champions League, Europa League ak kalandriye 5 chanpyona yo. Kle football-data.org la opsyonèl, men li itil si plan gratis API-Football la pa bay sezon kounye a:

| Konpetisyon | Sous | Kle |
|---|---|---|
| Champions League | football-data.org (gratis) | `FOOTBALL_DATA_TOKEN` |
| Europa League | API-Football (plan gratis, 100 demann pa jou) | `APIFOOTBALL_KEY` |

1. Kreye yon kont sou https://www.football-data.org/client/register. Yo voye kle a ba ou pa imel.
2. Kreye yon kont sou https://dashboard.api-football.com/register. Kle a nan **Account → My Access**.
3. Mete kle yo nan fichye `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Kole chak kle apre siy `=` la, epi anrejistre (**Ctrl+O**, **Enter**, **Ctrl+X**).
4. Telechaje match yo:
   ```bash
   python3 scripts/fetch_europe.py
   ```
   Apre sa, `fetch_data.py` ap telechaje yo otomatikman chak fwa.

Pou analize yon match:
```bash
python3 scripts/analyze_match.py "Arsenal" "Bayern Munich" --europe CL
python3 scripts/analyze_match.py "Roma" "Porto" --europe EL
```
Nan Claude Code: `/analiz Arsenal vs Bayern Champions League`

**Kijan l mache pou koup yo:**
- **Fòm nan** melanje match chanpyona lokal la ak match Ewòp yo (10 dènye match, tout konpetisyon).
- Pou ekip ki soti nan lòt peyi (Pòtigal, Olann, Bèljik, Tiki, Ekos, Grès), pwojè a telechaje chanpyona pa yo tou.
- **Modèl la** konpare ekip ki soti nan peyi diferan ak yon fòs apwoksimatif pou chak chanpyona. Li mwens presi pase pou match chanpyona.
- **Kònè yo** soti nan match chanpyona lokal yo sèlman.
- Pa gen kòt bookmaker nan done gratis yo. Ajan an chèche yo sou entènèt.
- Si sous API-Football la sèvi, analiz la ka jwenn blesi otomatikman tou.

> **Atansyon:** Plan gratis API-Football la ka pa bay sezon kounye a. Si `fetch_europe.py` di sit la refize, Europa League ap mache sèlman ak rechèch ajan an fè sou entènèt. Champions League ap kontinye mache ak football-data.org.

---

## 3. Sèvi ak ajan an nan Claude Code

Nan dosye pwojè a:
```bash
claude
```
Apre sa, tape youn nan kòmand sa yo:
```
/analiz Arsenal vs Chelsea
/analiz Real Madrid vs Barcelona
/analiz match Serie A wikenn sa a
```
Ou ka mande l tou nan pwòp mo pa w, pa egzanp: *"Analize match PSG kont Marseille"*.

Men sa ajan an fè:
1. Li mete done yo ajou si yo gen plis pase 24 è.
2. Li kalkile estatistik yo ak pousantaj yo.
3. Li chèche blesi, estad, move tan ak enpòtans match la sou entènèt.
4. Li ekri analiz la an Kreyòl.
5. Li kreye rapò a nan `reports/`.

**San Claude Code**, ou ka toujou fè pati estatistik la poukont ou:
```bash
python3 scripts/analyze_match.py "Arsenal" "Chelsea"
python3 scripts/build_report.py data/analysis/arsenal-vs-chelsea.json
```

---

## 4. Sit live: wè tout match yo sou telefòn

Sit la mete tèt li ajou otomatikman sou GitHub, **2 fwa pa jou**. Chak fwa, li:
1. telechaje done yo,
2. analize tout match 8 jou k ap vini yo (5 chanpyona + Champions League + Europa League),
3. pibliye yon paj akèy ak tout match yo, yon bouton chèche, ak filt pa konpetisyon.

Ou klike sou yon match pou w wè rapò konplè a. Tout bagay gratis, epi pa gen sèvè pou w jere.

### Konfigirasyon (yon sèl fwa)

**a. Mete kòd la sou GitHub**
1. Sou github.com, kreye yon nouvo depo ki rele `analis-foutbol`. Li dwe **Public**, paske GitHub Pages gratis la mache sèlman ak depo piblik.
2. Nan Terminal la, depi dosye pwojè a:
   ```bash
   git init
   git add .
   git commit -m "Premye vèsyon"
   git branch -M main
   git remote add origin https://github.com/SteveJ509/analis-foutbol.git
   git push -u origin main
   ```
   Fichye `.env` la p ap monte sou GitHub, paske li nan `.gitignore`.

**b. Mete kle API yo nan GitHub (pou Champions League ak Europa League)**
Ale nan **Settings → Secrets and variables → Actions → New repository secret**, epi kreye 2 sekrè:
- `FOOTBALL_DATA_TOKEN`: kle football-data.org ou a
- `APIFOOTBALL_KEY`: kle API-Football ou a

Sekrè yo kache: pèsonn pa ka wè yo, menm si depo a piblik.

**c. Aktive GitHub Pages**
Ale nan **Settings → Pages**. Anba **Source**, chwazi **GitHub Actions**.

**d. Lanse premye mizajou a**
Ale nan onglet **Actions**, klike sou **Mete sit la ajou**, epi sou **Run workflow**. Tann 1-2 minit jiskaske ou wè yon ✓ vèt.

Sit ou a ap la:
**https://stevej509.github.io/analis-foutbol/**

Ajoute l sou ekran telefòn ou (**Add to Home screen**), konsa l ap ouvri tankou yon aplikasyon.

### Analiz otomatik ak analiz ajan an

- **Sou sit la**, chak match gen yon analiz otomatik ki baze sou chif yo sèlman.
- **Pou yon analiz konplè** ak blesi, estad, move tan ak enpòtans match la, lanse `/analiz` nan Claude Code pou match la. Apre sa, voye analiz la sou GitHub:
  ```bash
  git add data/context
  git commit -m "Analiz match"
  git push
  ```
  Sit la ap mete tèt li ajou nan kèk minit, epi analiz ajan an ap ranplase analiz otomatik la.

### Si yon bagay pa mache

Nan onglet **Actions**, klike sou dènye lansman an pou w li mesaj erè a. Kopye l voye ban mwen.

### Teste sit la sou Chromebook ou anvan

```bash
python3 scripts/fetch_data.py
python3 scripts/build_site.py
```
Apre sa, nan aplikasyon **Files**, ale nan **Linux files → analis-foutbol → site**, epi ouvri `index.html`.

## Bagay pou w konnen

- Pou match chanpyona, estatistik yo se match chanpyona sèlman. Pou match Ewòp, fòm nan gen tout konpetisyon.
- Sit football-data.co.uk mete rezilta yo ajou kèk fwa pa semèn. Kòt match k ap vini yo konn parèt vandredi (pou wikenn nan) ak madi (pou match nan mitan semèn nan).
- **Pousantaj yo se estimasyon, pa garanti.** Foutbòl gen anpil sipriz. Si w parye, pa janm mize plis lajan pase sa w ka pèdi.

## Dosye yo

```
analis-foutbol/
├── CLAUDE.md                     # enstriksyon pou Claude Code
├── .env.example                  # modèl pou kle API yo
├── .claude/agents/analis-foutbol.md   # ajan an
├── .claude/commands/analiz.md         # kòmand /analiz
├── scripts/
│   ├── config.py                 # chanpyona, sezon, non ekip
│   ├── fetch_data.py             # telechaje done yo
│   ├── fetch_europe.py           # Champions League + Europa League
│   ├── footdata.py               # li fichye CSV yo
│   ├── analyze_match.py          # estatistik + modèl
│   ├── build_report.py           # rapò HTML
│   ├── build_site.py             # konstwi sit la (tout match k ap vini yo)
│   └── context_example.json      # egzanp kontèks ajan an ekri
├── data/                         # done ak analiz (kreye otomatikman)
├── reports/                      # rapò HTML yo
├── site/                         # sit la (kreye otomatikman)
└── .github/workflows/sit.yml     # mete sit la ajou 2 fwa pa jou
```
