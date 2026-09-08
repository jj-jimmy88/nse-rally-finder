"""Open a GitHub issue (which GitHub emails to the repo owner) when the day's run produced new buy signals.
Uses the workflow's built-in GITHUB_TOKEN via the gh CLI — no secrets needed. FORCE_TEST=1 posts a sample issue."""
import json, os, subprocess, sys
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
L=json.load(open(os.path.join(D,"latest.json"))); sig=L["new_signals"]; test=os.environ.get("FORCE_TEST")=="1"
if test and not sig:
    sig=[dict(rule="R-A",symbol="MENONBE",industry="Auto Components & Equipments",signal_close=308.55,mcap=1851,pe=42.1,pgrowth=41,lo250=3.01,prom_buy_date="")]
if not sig: print("no new signals — no issue"); sys.exit(0)
syms=", ".join(s["symbol"] for s in sig)
title=("[TEST] " if test else "")+f"[Rally Finder] {len(sig)} new buy signal(s) for tomorrow — {syms}"
rows="\n".join(f"| {s['rule']} | **{s['symbol']}** | {s.get('industry','')} | ₹{s.get('signal_close','')} | {s['mcap']} | {s['pe']} | {s['pgrowth']}% | {s['lo250']}× | {s.get('prom_buy_date') or '—'} |" for s in sig)
body=f"""{'**This is a one-time test of the notification path — real issues only appear on days with new signals.**' if test else ''}
Signals computed on NSE data through **{L['last_data_date']}**. Rule: buy at the next day's open, −10% stop on the intraday low, hold 40 trading days, take every signal, size each at 2–3% of capital.

| Rule | Stock | Industry | Signal close | Mcap ₹cr | P/E | Profit growth | × off 52-wk low | Promoter buy |
|---|---|---|---|---|---|---|---|---|
{rows}

Dashboard: https://jj-jimmy88.github.io/nse-rally-finder/

_Backtest 2023–26: ~27 signals/yr, 20% reach +50%, avg +8% per trade with the stop. Not investment advice._"""
r=subprocess.run(["gh","issue","create","--title",title,"--body",body,"--label","signal"],capture_output=True,text=True)
if r.returncode!=0 and "not found" in (r.stderr or "").lower():
    subprocess.run(["gh","label","create","signal","--color","0F6E56","--description","daily buy signal"],capture_output=True,text=True)
    r=subprocess.run(["gh","issue","create","--title",title,"--body",body,"--label","signal"],capture_output=True,text=True)
print(r.stdout, r.stderr); sys.exit(r.returncode)
