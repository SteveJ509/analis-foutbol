---
description: Fè 2 konbinezon wikenn yo (kòt ~5 ak kòt ~10) epi verifye blesi, teren ak enpòtans chak match
---

Sèvi ak ajan `parieur-pro` la (`.claude/agents/parieur-pro.md`): swiv règ li yo ak lis bagay yon pro tcheke yo. Pale an Kreyòl ayisyen. Pa janm envante yon blesi oswa yon nouvèl.

## 1. Kandida yo
```bash
python3 scripts/fetch_data.py
python3 scripts/combo.py --json
```
Li `data/combo_auto.json`. Li gen 2 konbinezon otomatik yo (`konbinezon`) ak tout seleksyon ki kalifye yo (`rezèv`). Chak seleksyon gen omwen 85% chans dapre modèl la, ki korije ak backtest la.

## 2. Verifye chak match (WebSearch / WebFetch)
Pou chak seleksyon nan 2 konbinezon yo, chèche:
- **Blesi ak suspansyon** (sit klib la, BBC, ESPN, Marca, Kicker, L'Équipe, Gazzetta...) ak **jwè kle ki absan**
- **Enpòtans match la**: batay pou tit, Ewòp, desant, derby; èske ekip la jwe Ewòp nan mitan semèn nan (risk woulman); chanjman antrenè
- **Teren ak move tan**: gwo lapli, nèj, van, teren an move kondisyon

Kesyon pou chak seleksyon: **èske kontèks la kontredi seleksyon an?** Egzanp:
- "Over 1.5" men 2 premye atakan yo absan, oswa gwo lapli prevwa → retire
- "1X" pou yon ekip ki pral fè woulman paske l jwe Champions League madi → retire
- "Under 3.5" nan yon derby kote 2 ekip yo bezwen genyen → reflechi
- Si yon enfòmasyon pa sèten, pa retire seleksyon an pou sa sèlman, men ekri l nan `nòt`.

## 3. Ranplase sa ou retire yo
Pran nouvo seleksyon nan `rezèv` (yon sèl pa match, pa repete match ki deja nan menm konbinezon an). Verifye yo tou. Kontinye jiskaske:
- **k5**: kòt total (pwodui `kòt_jis` yo) ant 4.5 ak 6
- **k10**: kòt total ant 9 ak 12, ak lòt match pase k5 si posib

## 4. Ekri chwa ou yo
Ekri `data/context/konbinezon_draft.json`:
```json
{
  "k5": [{"slug": "...", "mache": "H_O0.5", "nòt": "Tou de atakan titilè yo la; pa gen lapli.", "rezilta": ""}],
  "k10": [{"slug": "...", "mache": "1X", "nòt": "..."}],
  "retire": [{"match": "Ekip A vs Ekip B", "rezon": "Premye bitè a blese, ekip la ap fè woulman"}],
  "chanjman": "Kout: sa ki chanje nan mizajou sa a ak poukisa (vid si se premye vèsyon an)",
  "rezime": "2-3 fraz an Kreyòl sou konbinezon wikenn nan."
}
```
Apre sa:
```bash
python3 scripts/combo.py --from-agent data/context/konbinezon_draft.json
python3 scripts/build_site.py
git add data/context/konbinezon.json data/context/konbinezon_draft.json
git commit -m "Konbinezon wikenn verifye"
git push
```
Sit la ap montre konbinezon yo ak etikèt "✅ Verifye pa ajan an" nan kèk minit.

## 5. Repons final
Bay itilizatè a 2 konbinezon yo (match, mache, %, kòt jis), sa ou retire ak rezon yo, ak kòt total ak chans total chak konbinezon. Raple l: kòt bookmaker yo ap pi ba pase kòt jis yo, epi chans pou tout seleksyon yo pase piti menm si chak seleksyon gen ≥85%.
