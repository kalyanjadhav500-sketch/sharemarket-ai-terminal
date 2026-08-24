import pandas as pd
import numpy as np
from quant_engine import add_indicators

def backtest_vwap_momentum(df, initial_capital=1_000_000, risk_pct=0.5, min_rr=1.8):
    if df.empty or len(df)<80:
        return {"error":"Not enough historical data for backtest."}, pd.DataFrame()
    x=add_indicators(df).dropna().copy()
    trades=[]
    capital=float(initial_capital)
    risk_fraction=risk_pct/100
    for i in range(40,len(x)-2):
        row=x.iloc[i]
        prev=x.iloc[i-1]
        atr=row["ATR"]
        if not np.isfinite(atr) or atr<=0:
            continue
        long_cond=(row["Close"]>row["VWAP"] and row["EMA_9"]>row["EMA_21"] and row["RSI"]>55 and row["REL_VOLUME"]>=1.2 and row["Close"]>prev["Close"])
        short_cond=(row["Close"]<row["VWAP"] and row["EMA_9"]<row["EMA_21"] and row["RSI"]<45 and row["REL_VOLUME"]>=1.2 and row["Close"]<prev["Close"])
        if not (long_cond or short_cond):
            continue
        entry=float(row["Close"])
        direction=1 if long_cond else -1
        sl=entry-direction*atr
        tp=entry+direction*1.8*atr
        risk_per_share=abs(entry-sl)
        if risk_per_share<=0: continue
        qty=max(1,int((capital*risk_fraction)/risk_per_share))
        result=None; exit_price=None
        for j in range(i+1,min(i+21,len(x))):
            bar=x.iloc[j]
            if direction==1:
                if bar["Low"]<=sl: result="LOSS"; exit_price=sl; break
                if bar["High"]>=tp: result="WIN"; exit_price=tp; break
            else:
                if bar["High"]>=sl: result="LOSS"; exit_price=sl; break
                if bar["Low"]<=tp: result="WIN"; exit_price=tp; break
        if result is None:
            exit_price=float(x.iloc[min(i+20,len(x)-1)]["Close"])
            result="WIN" if (exit_price-entry)*direction>0 else "LOSS"
        pnl=(exit_price-entry)*direction*qty
        capital+=pnl
        trades.append({"time":x.index[i],"direction":"BUY" if direction==1 else "SELL","entry":entry,"exit":exit_price,"qty":qty,"pnl":pnl,"result":result})
    t=pd.DataFrame(trades)
    if t.empty:
        return {"trades":0,"win_rate":0,"profit_factor":0,"max_drawdown":0,"total_pnl":0,"final_capital":capital}, t
    wins=t.loc[t.pnl>0,"pnl"]; losses=t.loc[t.pnl<0,"pnl"]
    equity=initial_capital+t["pnl"].cumsum()
    peak=equity.cummax()
    dd=(equity-peak)/peak*100
    pf=float(wins.sum()/abs(losses.sum())) if len(losses) and losses.sum()!=0 else float("inf")
    metrics={
        "trades":int(len(t)),
        "win_rate":round(float((t.pnl>0).mean()*100),2),
        "profit_factor":round(pf,2) if np.isfinite(pf) else "INF",
        "max_drawdown":round(float(dd.min()),2),
        "total_pnl":round(float(t.pnl.sum()),2),
        "final_capital":round(float(capital),2),
        "avg_pnl":round(float(t.pnl.mean()),2),
        "avg_r":round(float(t.pnl.abs().mean()/max(1,initial_capital*risk_fraction)),2)
    }
    return metrics,t
