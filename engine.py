"""NSE Small-Cap Rally Finder — daily signal engine.
Applies the two rules from the backtest to the latest trading day, point-in-time:
  Gate  : mcap > 1,000 cr, P/E < 50 (TTM from quarterly net profit, else last annual), annual profit growth > 20%
  R-A   : close >= 97% of 52-wk high, close >= 3x 52-wk low, mcap < 2,000 cr, open gap < 2%, month Apr-Dec
  PB    : promoter open-market buy in last 90 days, close >= 90% of 52-wk high, r20 > 10%, r60 > 20%, mcap < 3,000 cr
Reads data/*.json + data/prices.csv.gz, writes data/signals.json and data/latest.json.
"""
import json, os, datetime as dt, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
def num(x):
    if x is None: return np.nan
    x=str(x).replace(",","").replace("%","").replace("₹","").replace("Cr.","").strip()
    try: return float(x)
    except: return np.nan
def lab2date(l):
    try: return pd.to_datetime("01 "+l,format="%d %b %Y")+pd.offsets.MonthEnd(0)
    except: return pd.NaT

def load_prices():
    import glob
    P=pd.concat([pd.read_csv(f,parse_dates=["date"]) for f in sorted(glob.glob(os.path.join(D,"prices_*.csv.gz")))],ignore_index=True)
    P=P[(P.close>0)&(P.open>0)].drop_duplicates(["symbol","date"]).sort_values(["symbol","date"]).reset_index(drop=True)
    return P

def fundamentals_panel(P):
    """Point-in-time gate inputs merged onto the price panel (same timing rules as the backtest)."""
    F=json.load(open(os.path.join(D,"fundamentals.json"))); FV=json.load(open(os.path.join(D,"symbols.json")))["face_value"]
    Q=[];A=[];SH=[]
    for s,v in F.items():
        fv=num(v.get("fv")) if v.get("fv") is not None else FV.get(s,np.nan)
        if v.get("q_np"):
            for lab,x in zip(v["qh"],v["q_np"]):
                d=lab2date(lab)
                if pd.notna(d) and pd.notna(num(x)): Q.append((s,d,num(x)))
        if v.get("p_np"):
            for lab,x in zip(v["ph"],v["p_np"]):
                if lab=="TTM": continue
                d=lab2date(lab)
                if pd.notna(d) and pd.notna(num(x)): A.append((s,d,num(x)))
        if v.get("b_ec") and fv and fv>0:
            for lab,x in zip(v["bh"],v["b_ec"]):
                d=lab2date(lab)
                if pd.notna(d) and num(x)>0: SH.append((s,d,num(x)*1e7/fv))
    Q=pd.DataFrame(Q,columns=["symbol","qend","np"]).sort_values(["symbol","qend"]); A=pd.DataFrame(A,columns=["symbol","fy","np_a"]).sort_values(["symbol","fy"]); SH=pd.DataFrame(SH,columns=["symbol","fy","shares"]).sort_values(["symbol","fy"])
    Q["ttm"]=Q.groupby("symbol").np.transform(lambda x:x.rolling(4).sum()); Q["date"]=Q.qend+pd.Timedelta(days=45)
    A["pgrowth"]=A.np_a/A.groupby("symbol").np_a.shift(1).abs()-1; A["date"]=A.fy+pd.Timedelta(days=62)
    SH["date"]=SH.fy+pd.Timedelta(days=62)
    P=P.sort_values("date")
    P=pd.merge_asof(P,Q[["symbol","date","ttm"]].sort_values("date"),on="date",by="symbol",direction="backward")
    P=pd.merge_asof(P,A[["symbol","date","pgrowth","np_a"]].sort_values("date"),on="date",by="symbol",direction="backward")
    P=pd.merge_asof(P,SH[["symbol","date","shares"]].sort_values("date"),on="date",by="symbol",direction="backward")
    P["ttm"]=P.ttm.fillna(P.np_a)
    P["mcap"]=P.close*P.shares/1e7; P["pe"]=np.where(P.ttm>0,P.mcap/P.ttm,np.nan)
    P["pass_gate"]=(P.mcap>1000)&(P.pe<50)&(P.pgrowth>0.20)
    return P.sort_values(["symbol","date"]).reset_index(drop=True)

def features(P):
    g=P.groupby("symbol")
    P["hi250"]=P.close/g.close.transform(lambda x:x.rolling(250,min_periods=200).max())
    P["lo250"]=P.close/g.close.transform(lambda x:x.rolling(250,min_periods=200).min())
    P["r20"]=g.close.pct_change(20); P["r60"]=g.close.pct_change(60)
    P["gap"]=P.open/g.close.shift(1)-1
    P["month"]=P.date.dt.month
    return P

def insider_flag(P):
    I=json.load(open(os.path.join(D,"insider.json")))["rows"]
    df=pd.DataFrame(I,columns=["symbol","date","value"]); df["date"]=pd.to_datetime(df.date)
    last=P.date.max()
    P["prom_buy_90"]=False; P["prom_buy_date"]=""
    if len(df):
        # for the latest day only (that is all we act on); historical flags come from the backtest file
        rec=df[(df.date>last-pd.Timedelta(days=90))&(df.date<=last)].groupby("symbol").date.max()
        m=P.date==last
        P.loc[m,"prom_buy_90"]=P.loc[m,"symbol"].isin(rec.index).values
        P.loc[m,"prom_buy_date"]=P.loc[m,"symbol"].map(rec.dt.strftime("%Y-%m-%d")).fillna("").values
    return P

def signals_for_day(P,day):
    X=P[(P.date==day)&(P.pass_gate==True)&P.hi250.notna()].copy()
    ra=(X.hi250>=.97)&(X.lo250>3)&(X.mcap<2000)&(X.gap<.02)&(~X.month.isin([1,2,3]))
    pb=(X.r20>.1)&(X.r60>.2)&(X.mcap<3000)&(X.hi250>=.9)&(X.prom_buy_90==True)
    X["rule"]=np.where(ra&pb,"R-A + PB",np.where(ra,"R-A",np.where(pb,"PB","")))
    return X[X.rule!=""]

def main():
    P=load_prices(); P=fundamentals_panel(P); P=features(P); P=insider_flag(P)
    last=P.date.max()
    sig_path=os.path.join(D,"signals.json")
    S=json.load(open(sig_path)) if os.path.exists(sig_path) else {"signals":[]}
    hist={(s["symbol"],s["signal_date"]) for s in S["signals"]}
    F=json.load(open(os.path.join(D,"fundamentals.json")))
    new=[]
    X=signals_for_day(P,last)
    for r in X.itertuples():
        # one signal per stock per 56 days (same dedupe as the backtest)
        prior=[s for s in S["signals"] if s["symbol"]==r.symbol and (last-pd.Timestamp(s["signal_date"])).days<=56]
        if prior or (r.symbol,last.strftime("%Y-%m-%d")) in hist: continue
        rec=dict(symbol=r.symbol,industry=(F.get(r.symbol) or {}).get("cls",""),rule=r.rule,signal_date=last.strftime("%Y-%m-%d"),
                 signal_close=round(float(r.close),2),mcap=round(float(r.mcap)),pe=round(float(r.pe),1),pgrowth=round(100*float(r.pgrowth)),
                 hi250=round(float(r.hi250),3),lo250=round(float(r.lo250),2),r20=round(100*float(r.r20),1),r60=round(100*float(r.r60),1),gap=round(100*float(r.gap),2),
                 prom_buy_date=r.prom_buy_date or "",entry_price=None,entry_date=None)
        new.append(rec); S["signals"].append(rec)
    # fill entry (next day's open) and track outcomes for open signals
    byS={s:g.set_index("date") for s,g in P.groupby("symbol")}
    for s in S["signals"]:
        g=byS.get(s["symbol"])
        if g is None: continue
        sd=pd.Timestamp(s["signal_date"]); after=g[g.index>sd]
        if len(after) and s.get("entry_price") is None:
            s["entry_price"]=round(float(after.open.iloc[0]),2); s["entry_date"]=after.index[0].strftime("%Y-%m-%d")
        if s.get("entry_price"):
            fw=after.iloc[:41]; e=s["entry_price"]
            s["days"]=int(len(fw))-1 if len(fw) else -1
            if len(fw):
                s["peak"]=round(float(fw.high.max()/e*100-100),1); s["low"]=round(float(fw.low.min()/e*100-100),1)
                s["last_close"]=round(float(fw.close.iloc[-1]),2); s["last_ret"]=round(float(fw.close.iloc[-1]/e*100-100),1)
                st=fw[fw.low/e*100-100<=-10]; s["stop_day"]=int(list(fw.index).index(st.index[0])) if len(st) else None
                hr=fw[fw.high/e*100-100>=50]; s["home_run_day"]=int(list(fw.index).index(hr.index[0])) if len(hr) else None
                s["closed"]=bool(len(fw)>=41)
    S["signals"].sort(key=lambda s:s["signal_date"])
    S["last_data_date"]=last.strftime("%Y-%m-%d"); S["updated_utc"]=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    json.dump(S,open(sig_path,"w"),indent=0)
    I=json.load(open(os.path.join(D,"insider.json"))); Fd=json.load(open(os.path.join(D,"fundamentals.json")))
    latest=dict(last_data_date=S["last_data_date"],updated_utc=S["updated_utc"],new_signals=new,
                candidates_today=int(((P.date==last)&(P.pass_gate==True)).sum()),symbols_with_price=int((P.date==last).sum()),
                insider_data_date=I.get("fetched"),fundamentals_date=sorted(v.get("fetched","") for v in Fd.values())[len(Fd)//2] if Fd else "")
    json.dump(latest,open(os.path.join(D,"latest.json"),"w"),indent=1)
    print(f"data through {S['last_data_date']}: {latest['symbols_with_price']} priced, {latest['candidates_today']} pass the gate, {len(new)} new signal(s):",[(n['symbol'],n['rule']) for n in new])
    return latest
if __name__=="__main__": main()
