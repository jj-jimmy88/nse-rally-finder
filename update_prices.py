"""Append the latest daily OHLCV for every symbol from Yahoo Finance (NSE suffix .NS). Keeps a 330-day rolling window."""
import json, os, sys, time, numpy as np, pandas as pd, yfinance as yf
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
import glob
P=pd.concat([pd.read_csv(f,parse_dates=["date"]) for f in sorted(glob.glob(os.path.join(D,"prices_*.csv.gz")))],ignore_index=True)
syms=json.load(open(os.path.join(D,"symbols.json")))["symbols"]
period=sys.argv[1] if len(sys.argv)>1 else "1mo"
rows=[]
for i in range(0,len(syms),200):
    batch=syms[i:i+200]; tick=[s+".NS" for s in batch]
    for attempt in range(3):
        try:
            df=yf.download(tick,period=period,interval="1d",group_by="ticker",auto_adjust=False,actions=False,progress=False,threads=True)
            break
        except Exception as e:
            print("batch",i,"retry",attempt,e); time.sleep(20*(attempt+1)); df=None
    if df is None or df.empty: continue
    for s,t in zip(batch,tick):
        try:
            x=df[t] if isinstance(df.columns,pd.MultiIndex) else df
        except KeyError: continue
        x=x.dropna(subset=["Close"])
        for d,r in x.iterrows():
            if r["Open"]>0 and r["Close"]>0: rows.append((s,pd.Timestamp(d).normalize(),float(r["Open"]),float(r["High"]),float(r["Low"]),float(r["Close"]),int(r["Volume"]) if not np.isnan(r["Volume"]) else 0))
    time.sleep(2)
N=pd.DataFrame(rows,columns=["symbol","date","open","high","low","close","volume"])
print("fetched",len(N),"rows for",N.symbol.nunique(),"symbols; latest",N.date.max())
if len(N)==0: sys.exit("no data fetched")
# Yahoo occasionally revises the last few days; new rows replace old ones for the same symbol/date
P=pd.concat([P[~P.set_index(["symbol","date"]).index.isin(N.set_index(["symbol","date"]).index)],N]).sort_values(["symbol","date"])
P=P.groupby("symbol").tail(330)
P["date"]=P.date.dt.strftime("%Y-%m-%d")
for k in range(2):
    P[P.symbol.map(lambda x:hash(x)%2 if False else (sum(map(ord,x))%2))==k].to_csv(os.path.join(D,f"prices_{k}.csv.gz"),index=False,compression="gzip",float_format="%.2f")
print("prices now",len(P),"rows,",P.symbol.nunique(),"symbols, through",P.date.max())
