import sys, json, subprocess
sys.path.insert(0,'firewall')
from market_data import get
import pandas as pd
TICK = {"VANECK ETF TRUST":"SMH","NVIDIA CORPORATION":"NVDA","ORACLE CORP":"ORCL",
 "BROADCOM INC":"AVGO","ADVANCED MICRO DEVICES INC":"AMD","BLOOM ENERGY CORP":"BE",
 "SANDISK CORP":"SNDK","MICRON TECHNOLOGY INC":"MU","COREWEAVE INC":"CRWV",
 "TAIWAN SEMICONDUCTOR MANUFAC":"TSM","ASML HLDG NV N Y REGISTRY":"ASML",
 "IREN LIMITED":"IREN","CORE SCIENTIFIC INC NEW":"CORZ","APPLIED DIGITAL CORP":"APLD",
 "INTEL CORP":"INTC","RIOT PLATFORMS INC":"RIOT","CLEANSPARK INC":"CLSK",
 "SOLARIS ENERGY INFRAS INC":"SEI","T1 ENERGY INC":"TE","BITFARMS LTD":"BITF",
 "BITDEER TECHNOLOGIES GROUP":"BTDR","POWER SOLUTIONS INTL INC":"PSIX",
 "CORNING INC":"GLW","WHITEFIBER INC":"WYFI","BABCOCK &amp; WILCOX ENTERPRISES":"BW",
 "SHARONAI HOLDINGS INC":"SHAZ","PROPETRO HLDG CORP":"PUMP","INFOSYS LTD":"INFY",
 "HIVE DIGITAL TECHNOLOGIES LT":"HIVE"}
df = pd.read_csv("blindrun/13f_q1_2026.csv")
df["ticker"] = df["issuer"].map(TICK)
agg = df.groupby("ticker", as_index=False).agg(value_usd=("value_usd","sum"),
                                               shares=("shares","sum"),
                                               issuer=("issuer","first"))
rows=[]
for _,r in agg.iterrows():
    try:
        p = get(r.ticker, "2026-01-01")
        d = pd.read_csv(p)
        d["dv"] = d.close*d.volume
        adv = d.dv.tail(21).median()
        px_fire = d.close.iloc[-1]
        rows.append({"ticker":r.ticker,"issuer":r.issuer,"q1_value_usd":r.value_usd,
                     "q1_shares":r.shares,"px_at_fire":px_fire,
                     "value_at_fire":r.shares*px_fire,"adv_usd_21d":adv,
                     "days_of_adv":(r.shares*px_fire)/adv if adv else float("nan"),
                     "last_bar":d.date.iloc[-1]})
    except Exception as e:
        rows.append({"ticker":r.ticker,"issuer":r.issuer,"q1_value_usd":r.value_usd,
                     "q1_shares":r.shares,"error":str(e)[:60]})
out=pd.DataFrame(rows).sort_values("days_of_adv",ascending=False)
out.to_csv("blindrun/liquidity.csv",index=False)
print(out[["ticker","q1_value_usd","value_at_fire","adv_usd_21d","days_of_adv","last_bar"]]
      .to_string(index=False,float_format=lambda x:f"{x:,.1f}"))
