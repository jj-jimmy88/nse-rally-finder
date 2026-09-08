"""Refresh quarterly/annual net profit, equity capital and face value from screener.in for every symbol (run twice a month)."""
import json, os, sys, time, random, requests, pandas as pd
from bs4 import BeautifulSoup
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
F=json.load(open(os.path.join(D,"fundamentals.json"))); syms=json.load(open(os.path.join(D,"symbols.json")))["symbols"]
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36","Accept-Language":"en-US,en;q=0.9"}
today=pd.Timestamp.today().strftime("%Y-%m-%d")
def parse(html):
    s=BeautifulSoup(html,"html.parser"); out={}
    for sec,key in [("quarters","q"),("profit-loss","p"),("balance-sheet","b")]:
        t=s.select_one(f"section#{sec} table")
        if not t: continue
        hd=[th.get_text(strip=True) for th in t.select("thead th")][1:]; rows={}
        for tr in t.select("tbody tr"):
            tds=[td.get_text(strip=True) for td in tr.select("td")]
            if tds: rows[tds[0].rstrip("+").strip()]=tds[1:]
        out[key+"h"]=hd; out[key]=rows
    fv=None
    for li in s.select("#top-ratios li"):
        tx=li.get_text(" ",strip=True)
        if tx.startswith("Face Value"):
            try: fv=float(tx.split("₹")[-1].replace(",","").strip())
            except: pass
    out["fv"]=fv
    return out
sess=requests.Session(); sess.headers.update(H)
todo=[s for s in syms if (F.get(s,{}).get("fetched","")<today)]
limit=int(sys.argv[1]) if len(sys.argv)>1 else len(todo)
done=0; errs=0
for sym in todo[:limit]:
    got=None
    for path in (f"/company/{sym}/consolidated/",f"/company/{sym}/"):
        try:
            r=sess.get("https://www.screener.in"+path,timeout=30)
            if r.status_code==429: print("429 — sleeping 90s"); time.sleep(90); r=sess.get("https://www.screener.in"+path,timeout=30)
            if r.status_code!=200: continue
            o=parse(r.text)
            if o.get("q") and o["q"].get("Net Profit"): got=o; break
        except Exception as e: errs+=1; time.sleep(5)
        time.sleep(1.0+random.random())
    if got:
        old=F.get(sym,{})
        F[sym]=dict(fv=got.get("fv") or old.get("fv"),qh=got["qh"],q_np=got["q"].get("Net Profit"),ph=got.get("ph",[]),p_np=(got.get("p") or {}).get("Net Profit"),bh=got.get("bh",[]),b_ec=(got.get("b") or {}).get("Equity Capital"),cls=old.get("cls",""),fetched=today)
        done+=1
    else: errs+=1
    if done%50==0: json.dump(F,open(os.path.join(D,"fundamentals.json"),"w"))
    time.sleep(1.0+random.random())
json.dump(F,open(os.path.join(D,"fundamentals.json"),"w")); print("fundamentals refreshed",done,"errors",errs,"remaining",len(todo)-min(limit,len(todo)))
