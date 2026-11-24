"""Konpare plizyè estrateji pou konbinezon yo sou done reyèl (backtest)."""
import contextlib, io, math
import backtest as B
import combo as C

with contextlib.redirect_stdout(io.StringIO()):
    B.run()
weekend = B.LAST["weekend"]

def legs_for(items, allowed, lo, hi, pick):
    legs = []
    for a, m in items:
        cands = []
        for r in a["tout_mache"]:
            p = r["pousantaj"] / 100
            if r["mache"] in allowed and lo <= p <= hi:
                cands.append((p, r["mache"]))
        if cands:
            p, k = (min if pick == "lo" else max)(cands)
            legs.append((p, k, m))
    return legs

ALL = C.ALLOWED
GOALS = {"O0.5", "O1.5", "U4.5", "H_O0.5", "A_O0.5", "1X", "X2", "12", "DNB1", "DNB2", "U3.5"}
STRATS = {
    "A_aktyèl(lo,85-95)": (ALL, .85, .95, "lo", "asc"),
    "B_pi_sèten(hi,85-97)": (ALL, .85, .97, "hi", "desc"),
    "C_san_kònè(lo,85-95)": (GOALS, .85, .95, "lo", "asc"),
    "D_san_kònè(hi,88-97)": (GOALS, .88, .97, "hi", "desc"),
    "E_90+(hi,90-97)": (ALL, .90, .97, "hi", "desc"),
    "F_san_kònè_90+": (GOALS, .90, .97, "hi", "desc"),
}
for target in (5, 10):
    print(f"\n===== Kòt sib {target} =====")
    for name, (allowed, lo, hi, pick, order) in STRATS.items():
        w = won = nl = hits = 0; odds_l = []; chance_l = []
        fam = {}
        for wk, items in sorted(weekend.items()):
            if len(items) < 15: continue
            legs = legs_for(items, allowed, lo, hi, pick)
            legs.sort(key=lambda x: x[0], reverse=(order == "desc"))
            ch, o = [], 1.0
            for leg in legs:
                if o >= target or len(ch) >= 25: break
                ch.append(leg); o *= 1 / leg[0]
            if o < target * 0.85: continue
            w += 1; ok = True
            for p, k, m in ch:
                r = B.outcome(k, m["hg"], m["ag"], m["hc"], m["ac"])
                nl += 1; hits += int(bool(r)); ok = ok and bool(r)
                f = fam.setdefault(k, [0, 0]); f[0] += 1; f[1] += int(bool(r))
            won += ok; odds_l.append(o); chance_l.append(math.prod(x[0] for x in ch))
        if w:
            print(f"{name:<24} wikenn {w:>3} · genyen {won:>2} ({100*won/w:4.1f}%) · modèl te prevwa {100*sum(chance_l)/w:4.1f}% · "
                  f"seleksyon pase {100*hits/nl:4.1f}% · {nl/w:4.1f} seleksyon/konbinezon")
            if target == 5:
                print("   ", ", ".join(f"{k}:{100*v[1]/v[0]:.0f}%/{v[0]}" for k, v in sorted(fam.items(), key=lambda x: -x[1][0])[:8]))
