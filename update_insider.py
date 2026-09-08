"""Refresh promoter open-market purchases (NSE insider-trading disclosures) for the stocks that could trigger rule PB.
NSE's API needs browser-like headers and a warm-up cookie; if NSE blocks the runner the old data is kept and flagged."""
import json, os, time, datetime as dt, requests, pandas as pd, numpy as np
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
import engine
P=engine.load_prices(); P=engine.fundamentals_panel(P); P=engine.features(P)
last=P.date.max(); X=P[(P.date==last)&(P.pass_gate==True)&(P.hi250>=.88)&(P.r60>.15)&(P.mcap<3200)]
targets=sorted(X.symbol.unique()); print("candidate symbols for PB:",len(targets))
I=json.load(open(os.path.join(D,"insider.json"))); rows={(r[0],r[1],r[2]):r for r in I["rows"]}
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36","Accept":"*/*","Accept-Language":"en-US,en;q=0.9","Referer":"https://www.nseindia.com/companies-listing/corporate-filings-insider-trading"}
s=requests.Session(); s.headers.update(H)
ok=0; fail=0
try:
    s.get("https://www.nseindia.com/",timeout=20); time.sleep(1); s.get("https://www.nseindia.com/companies-listing/corporate-filings-insider-trading",timeout=20)
except Exception as e: print("warm-up failed",e)
for i,sym in enumerate(targets):
    try:
        r=s.get("https://www.nseindia.com/api/corporates-pit",params={"index":"equities","symbol":sym},timeout=20)
        if r.status_code!=200: fail+=1; time.sleep(3); continue
        for x in r.json().get("data",[]):
            if "Promoter" in (x.get("personCategory") or "") and str(x.get("tdpTransactionType","")).startswith("Buy") and "Market" in (x.get("acqMode") or "") and "Equity" in (x.get("secType") or "Equity"):
                d=pd.to_datetime(str(x.get("date",""))[:11],format="%d-%b-%Y",errors="coerce")
                if pd.notna(d):
                    try: v=float(str(x.get("secVal","0")).replace(",",""))
                    except: v=0.0
                    rows[(sym,d.strftime("%Y-%m-%d"),v)]=[sym,d.strftime("%Y-%m-%d"),v]
        ok+=1; time.sleep(1.2)
    except Exception as e:
        fail+=1; time.sleep(3)
print("insider refresh: ok",ok,"failed",fail)
if ok>0:
    I["rows"]=sorted(rows.values(),key=lambda r:r[1]); I["fetched"]=last.strftime("%Y-%m-%d"); I["last_refresh_ok"]=ok; I["last_refresh_failed"]=fail
    json.dump(I,open(os.path.join(D,"insider.json"),"w"))
else:
    I["last_refresh_failed"]=fail; json.dump(I,open(os.path.join(D,"insider.json"),"w")); print("WARNING: NSE blocked every request; promoter data unchanged (dated",I.get("fetched"),")")
