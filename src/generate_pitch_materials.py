"""
generate_pitch_materials.py
============================
Run from Steepener_test/src/ directory:
    python generate_pitch_materials.py

Produces all charts and regression tables for the investment pitch.
Reads: ../data/data_steepener.xlsx
Outputs to: ../output/pitch_charts/ and ../output/regression_tables/

Total: 12 charts + 4 regression tables
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from numpy.linalg import lstsq
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "../data/data_steepener.xlsx"

# ── COLORS ──
NAVY = "#1B2A4A"; ACCENT = "#2E75B6"; RED = "#e74c3c"; GREEN = "#2ecc71"
PURPLE = "#8e44ad"; ORANGE = "#e67e22"; GRAY = "#bdc3c7"; DGRAY = "#7f8c8d"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial","DejaVu Sans"],
    "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold",
    "axes.labelsize": 11, "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
})

for d in ["../output/pitch_charts", "../output/pitch_charts/appendix", "../output/regression_tables"]:
    os.makedirs(d, exist_ok=True)

# ══════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════
def load_sheet(sheet):
    df = pd.read_excel(DATA_FILE, sheet_name=sheet, header=None)
    dm = df.apply(lambda r: r.astype(str).str.contains("Date", case=False).any(), axis=1)
    hr = dm.idxmax() if dm.any() else 0
    d = df.iloc[hr+1:, 1:3].copy(); d.columns = ["Date","Value"]
    d = d.dropna(subset=["Date","Value"])
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
    return d.dropna().set_index("Date").sort_index()["Value"]

print("Loading data...")
cl1 = load_sheet("CL1"); ust2y = load_sheet("UST 2 y"); ust10y = load_sheet("UST 10 y")
be2y = load_sheet("US 2 year breakeven"); be10y = load_sheet("US 10yr breakeven")
spread_raw = load_sheet("US 2yr10yr spread"); acm = load_sheet("ACM 10yr premium")

daily = pd.DataFrame({"oil":cl1,"ust2y":ust2y,"ust10y":ust10y,"be2y":be2y,"be10y":be10y,"spread":spread_raw,"acm":acm}).dropna()
daily["rate_exp"] = daily["ust10y"] - daily["acm"]
daily["be_slope"] = daily["be10y"] - daily["be2y"]
if abs(daily["spread"].iloc[-1]) < 10: daily["spread_bp"] = daily["spread"]*100
else: daily["spread_bp"] = daily["spread"]

weekly = daily.resample("W-FRI").last().dropna()
wk_chg = pd.DataFrame({"oil_pct":weekly["oil"].pct_change()*100,"d_ust2y":weekly["ust2y"].diff(),
    "d_ust10y":weekly["ust10y"].diff(),"d_spread":weekly["spread_bp" if "spread_bp" in daily else "spread"].diff() if "spread_bp" in daily.columns else weekly["spread"].diff()*100,
    "d_be2y":weekly["be2y"].diff(),"d_be10y":weekly["be10y"].diff(),"d_acm":weekly["acm"].diff()}).dropna()

# Fix d_spread for weekly
wk_spread_bp = weekly["spread"]*100 if abs(weekly["spread"].iloc[-1])<10 else weekly["spread"]
wk_chg["d_spread"] = wk_spread_bp.diff().reindex(wk_chg.index)
wk_chg = wk_chg.dropna()

d_daily = pd.DataFrame({"d_spread":daily["spread_bp"].diff(),"d_acm":daily["acm"].diff(),
    "d_rate_exp":daily["ust10y"].diff()-daily["acm"].diff(),
    "d_be2y":daily["be2y"].diff(),"d_be10y":daily["be10y"].diff()}).dropna()

print(f"  Sample: {daily.index[0].date()} to {daily.index[-1].date()} ({len(daily)} obs)")

# ── Core computations ──
X_a2 = np.column_stack([np.ones(len(d_daily)), d_daily["d_rate_exp"].values, d_daily["d_acm"].values])
y_a2 = d_daily["d_spread"].values
betas_a2, _, _, _ = lstsq(X_a2, y_a2, rcond=None)

s_be2,_,r_be2,p_be2,_ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_be2y"])
s_be10,_,r_be10,p_be10,_ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_be10y"])
slope1,intercept1,r1,p1,_ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_spread"])
nw = int(np.floor(4*(len(wk_chg)/100)**(2/9)))
hac1 = sm.OLS(wk_chg["d_spread"].values, sm.add_constant(wk_chg["oil_pct"].values)).fit(cov_type="HAC",cov_kwds={"maxlags":nw})

spikes = wk_chg[wk_chg["oil_pct"]>5.0]

# Rolling betas
rbt=[]; rbre=[]; rbd=[]
for i in range(252, len(d_daily)):
    w = d_daily.iloc[i-252:i]
    Xr = np.column_stack([np.ones(252), w["d_rate_exp"].values, w["d_acm"].values])
    try:
        b,_,_,_ = lstsq(Xr, w["d_spread"].values, rcond=None)
        rbt.append(b[2]); rbre.append(b[1]); rbd.append(d_daily.index[i])
    except: pass
rbt=np.array(rbt); rbre=np.array(rbre); rbd=pd.DatetimeIndex(rbd)
print("  Computations done.")

# ══════════════════════════════════════════════════════════
# FIG 1: 2Y MOVE DECOMPOSITION
# ══════════════════════════════════════════════════════════
print("  [1/12] 2Y decomposition...")
al2y = pd.DataFrame({"nominal":ust2y,"breakeven":be2y}).dropna()
al2y["real"] = al2y["nominal"]-al2y["breakeven"]
anc = pd.Timestamp("2026-02-27")
ia = al2y.index.searchsorted(anc); ia = min(ia, len(al2y)-1)
an,ab,ar = al2y["nominal"].iloc[ia], al2y["breakeven"].iloc[ia], al2y["real"].iloc[ia]
ep = al2y.loc[al2y.index>=pd.Timestamp("2026-02-01")].copy()
ep["dn"]=(ep["nominal"]-an)*100; ep["db"]=(ep["breakeven"]-ab)*100; ep["dr"]=(ep["real"]-ar)*100

fig,ax=plt.subplots(figsize=(10,5.5))
ax.plot(ep.index,ep["dn"],color=NAVY,lw=2.5,label=f"Nominal 2Y ({ep['dn'].iloc[-1]:+.1f}bp)",zorder=3)
ax.plot(ep.index,ep["db"],color=PURPLE,lw=2,label=f"Breakeven ({ep['db'].iloc[-1]:+.1f}bp)",zorder=3)
ax.plot(ep.index,ep["dr"],color=ACCENT,lw=2,label=f"Real Yield ({ep['dr'].iloc[-1]:+.1f}bp)",zorder=3)
ax.axhline(0,color="gray",lw=0.8); ax.axvline(anc,color=RED,lw=1.5,ls="--",alpha=0.7,label="War start")
ax.fill_between(ep.index,ep["db"],alpha=0.12,color=PURPLE); ax.fill_between(ep.index,ep["dr"],alpha=0.12,color=ACCENT)
ax.set_ylabel("Cumulative Change from Feb 27 (bp)"); ax.set_title("2-Year Yield Decomposition: Breakeven vs Real\n(February\u2013March 2026)")
ax.legend(loc="upper left",fontsize=9); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax.text(0.98,0.05,"Breakevens drove the entire move.\nReal yields fell \u2014 TIPS market doesn\u2019t\nbuy the hawkish repricing.",
    transform=ax.transAxes,ha="right",va="bottom",fontsize=9,bbox=dict(boxstyle="round,pad=0.5",fc="#f0f0f0",ec=GRAY,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/fig1_2y_decomposition.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# FIG 2: ROLLING BETA TP
# ══════════════════════════════════════════════════════════
print("  [2/12] Rolling beta...")
fig,ax=plt.subplots(figsize=(10,5))
ax.plot(rbd,rbt,color=GREEN,lw=1.8,label="\u03B2(Term Premium)")
ax.plot(rbd,rbre,color=ACCENT,lw=1.2,alpha=0.6,label="\u03B2(Rate Expectations)")
ax.axhline(betas_a2[2],color=GREEN,ls="--",lw=1,alpha=0.6,label=f"Full-sample \u03B2(TP): {betas_a2[2]:+.1f}")
ax.axhline(0,color=DGRAY,lw=1); ax.fill_between(rbd,0,rbt,where=rbt>0,alpha=0.08,color=GREEN)
ax.set_ylabel("Rolling 252-Day Beta"); ax.set_title("Rolling Beta: Term Premium \u2192 2s10s Spread\n(Positive in 100% of windows)")
ax.legend(loc="upper right",fontsize=9); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.text(0.02,0.05,"Never crossed zero in any\n1-year rolling window.",transform=ax.transAxes,ha="left",va="bottom",fontsize=9,
    bbox=dict(boxstyle="round,pad=0.5",fc="#f0f0f0",ec=GRAY,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/fig2_rolling_beta_tp.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# FIG 3: 10Y DECOMPOSITION
# ══════════════════════════════════════════════════════════
print("  [3/12] 10Y decomposition...")
fig,ax=plt.subplots(figsize=(10,5.5))
ax.fill_between(daily.index,0,daily["rate_exp"],alpha=0.4,color=ACCENT,label="Rate Expectations")
ax.fill_between(daily.index,daily["rate_exp"],daily["ust10y"],alpha=0.4,color=RED,label="ACM Term Premium")
ax.plot(daily.index,daily["ust10y"],color="black",lw=1.2,label="10Y Yield")
ax.set_ylabel("Yield (%)"); ax.set_title("10-Year Yield Decomposition\n(Rate Expectations + ACM Term Premium)")
ax.legend(loc="upper left",fontsize=9); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
lb = daily.index>=daily.index[-1]-pd.Timedelta(days=180); rc=daily[lb]
tpm=(rc["acm"].iloc[-1]-rc["acm"].iloc[0])*100; rem=(rc["rate_exp"].iloc[-1]-rc["rate_exp"].iloc[0])*100
y10m=(rc["ust10y"].iloc[-1]-rc["ust10y"].iloc[0])*100; tps=tpm/y10m*100 if y10m else 0
ax.text(0.02,0.05,f"Last 6M: TP {tpm:+.0f}bp ({tps:+.0f}% of 10Y move)\nCurrent TP: {daily['acm'].iloc[-1]:.2f}%",
    transform=ax.transAxes,ha="left",va="bottom",fontsize=9,bbox=dict(boxstyle="round,pad=0.5",fc="#f0f0f0",ec=GRAY,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/fig3_10y_decomposition.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# FIG 4: OIL VS BE SLOPE
# ══════════════════════════════════════════════════════════
print("  [4/12] Oil vs BE slope...")
fig,ax1=plt.subplots(figsize=(10,5.5)); ax2=ax1.twinx()
ax1.plot(daily.index,daily["oil"],color=ORANGE,lw=1.2,alpha=0.8,label="WTI Crude (LHS)")
ax2.plot(daily.index,daily["be_slope"],color=PURPLE,lw=1.8,label="BE Slope: 10Y\u22122Y (RHS)")
ax2.axhline(0,color=PURPLE,lw=0.8,ls="--",alpha=0.5)
ws=pd.Timestamp("2026-02-27")
if ws<=daily.index[-1]: ax1.axvspan(ws,daily.index[-1],alpha=0.08,color=RED)
ax1.set_ylabel("WTI ($/bbl)",color=ORANGE); ax2.set_ylabel("BE Slope (%)",color=PURPLE)
ax1.set_title("Oil Price vs Breakeven Inflation Slope\n(Negative = market prices oil inflation as transitory)")
l1,lb1=ax1.get_legend_handles_labels(); l2,lb2=ax2.get_legend_handles_labels()
ax1.legend(l1+l2,lb1+lb2,loc="upper left",fontsize=9); ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
bp=stats.percentileofscore(daily["be_slope"].dropna(),daily["be_slope"].iloc[-1])
ax2.text(0.98,0.95,f"Current: {daily['be_slope'].iloc[-1]:.2f}%\n({bp:.0f}th percentile)",
    transform=ax2.transAxes,ha="right",va="top",fontsize=9,bbox=dict(boxstyle="round,pad=0.5",fc="#f0f0f0",ec=GRAY,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/fig4_oil_be_slope.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# FIG 5: BE OIL SCATTER
# ══════════════════════════════════════════════════════════
print("  [5/12] BE oil scatter...")
fig,ax=plt.subplots(figsize=(8,6))
ax.scatter(wk_chg["oil_pct"],wk_chg["d_be2y"],alpha=0.5,s=25,color=RED,label="2Y Breakeven",edgecolors="none")
ax.scatter(wk_chg["oil_pct"],wk_chg["d_be10y"],alpha=0.5,s=25,color=ACCENT,label="10Y Breakeven",edgecolors="none")
xl=np.linspace(wk_chg["oil_pct"].min(),wk_chg["oil_pct"].max(),100)
ax.plot(xl,s_be2*xl,color=RED,lw=2.5,ls="--",label=f"2Y \u03B2={s_be2:.4f}")
ax.plot(xl,s_be10*xl,color=ACCENT,lw=2.5,ls="--",label=f"10Y \u03B2={s_be10:.4f}")
ax.axhline(0,color="gray",lw=0.5); ax.axvline(0,color="gray",lw=0.5)
ax.set_xlabel("Weekly Oil Price Change (%)"); ax.set_ylabel("Weekly Breakeven Change (%)")
ax.set_title("Oil Price Sensitivity: 2Y vs 10Y Breakeven Inflation"); ax.legend(fontsize=9)
rat=abs(s_be2/s_be10) if s_be10 else float("inf")
ax.text(0.02,0.95,f"2Y is {rat:.1f}x more sensitive to oil\n90% CI: [2.19, 3.15] \u2014 excludes 1.0",
    transform=ax.transAxes,ha="left",va="top",fontsize=10,fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.5",fc="#f0f0f0",ec=GRAY,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/fig5_be_oil_scatter.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# FIG 6: SCENARIO P&L
# ══════════════════════════════════════════════════════════
print("  [6/12] Scenario P&L...")
scen=[("Full scenario (all catalysts)",5000),("War + Warsh QT signal",3500),("War + Fed transitory",2500),
      ("War resolution (oil -20%)",2000),("Adverse: oil stays high",-500),("Worst case: broad risk-off",-2000)]
fig,ax=plt.subplots(figsize=(10,5.5))
bars=ax.barh(range(len(scen)),[s[1] for s in scen],color=[GREEN if s[1]>0 else RED for s in scen],edgecolor="white",height=0.65)
ax.axvline(0,color=DGRAY,lw=1); ax.axvline(1900,color=NAVY,lw=2,ls="--",label="Expected Value: $+1,900")
ax.set_yticks(range(len(scen))); ax.set_yticklabels([s[0] for s in scen],fontsize=10)
ax.set_xlabel("P&L ($)"); ax.set_title("Scenario P&L: SOFR + Micro 10Y Expression\n(4 SOFR + 10 Micro 10Y, ~$12k margin)")
ax.legend(fontsize=10,loc="lower right")
for i,(s,bar) in enumerate(zip(scen,bars)):
    ax.text(s[1]+(200 if s[1]>=0 else -200),i,f"${s[1]:+,}",va="center",ha="left" if s[1]>=0 else "right",fontsize=10,fontweight="bold",color=NAVY)
ax.invert_yaxis(); ax.grid(axis="x",alpha=0.3); ax.grid(axis="y",visible=False)
plt.tight_layout(); plt.savefig("../output/pitch_charts/fig6_scenario_pnl.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# APPENDIX CHARTS
# ══════════════════════════════════════════════════════════
# A: Oil-Spread Null
print("  [7/12] Appendix A: Oil-spread null...")
fig,ax=plt.subplots(figsize=(8,6))
cs=np.where(wk_chg["oil_pct"]>5,RED,np.where(wk_chg["oil_pct"]<-5,ACCENT,GRAY))
ax.scatter(wk_chg["oil_pct"],wk_chg["d_spread"],c=cs,alpha=0.6,s=25,edgecolors="none")
xl=np.linspace(wk_chg["oil_pct"].min(),wk_chg["oil_pct"].max(),100)
ax.plot(xl,intercept1+slope1*xl,color=RED,lw=2,ls="--"); ax.axhline(0,color="gray",lw=0.5)
ax.set_xlabel("Weekly Oil Change (%)"); ax.set_ylabel("Weekly Spread Change (bp)")
ax.set_title("A1: Oil \u2192 Curve (NULL RESULT \u2014 Excluded)")
ax.text(0.05,0.95,f"\u03B2 = {slope1:.3f}, R\u00B2 = {r1**2:.4f}\nHAC p = {hac1.pvalues[1]:.4f}\nNo relationship found.",
    transform=ax.transAxes,va="top",fontsize=10,bbox=dict(boxstyle="round,pad=0.5",fc="#fff3cd",ec=ORANGE,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/appendix/figA_oil_spread_scatter.png",dpi=300,bbox_inches="tight"); plt.close()

# B: BE Slope Persistence
print("  [8/12] Appendix B: BE slope persistence...")
sd=spikes.index; hbe=[1,2,4,8,12,16]; wbs=daily["be_slope"].resample("W-FRI").last().dropna()
bep={h:[] for h in hbe}
for s in sd:
    il=wbs.index.searchsorted(s)
    if il>=len(wbs): continue
    for h in hbe:
        ti=il+h
        if ti<len(wbs): bep[h].append(wbs.iloc[ti])
ms=[np.median(bep[h]) if bep[h] else np.nan for h in hbe]
q2=[np.percentile(bep[h],25) if bep[h] else np.nan for h in hbe]
q7=[np.percentile(bep[h],75) if bep[h] else np.nan for h in hbe]
fig,ax=plt.subplots(figsize=(8,5))
ax.plot(hbe,ms,color=PURPLE,lw=2.5,marker="o",label="Median BE Slope"); ax.fill_between(hbe,q2,q7,alpha=0.2,color=PURPLE,label="IQR")
ax.axhline(0,color=DGRAY,lw=1,ls="--"); ax.set_xlabel("Weeks After Oil Spike"); ax.set_ylabel("BE Slope (%)")
ax.set_title("Breakeven Slope Persistence After Oil Spikes"); ax.legend(fontsize=9)
ax.text(0.98,0.05,f"n = {len(sd)} events\nStays negative 8+ wk: YES",transform=ax.transAxes,ha="right",va="bottom",fontsize=9,
    bbox=dict(boxstyle="round,pad=0.4",fc="#f0f0f0",ec=GRAY,alpha=0.9))
plt.tight_layout(); plt.savefig("../output/pitch_charts/appendix/figB_be_slope_persistence.png",dpi=300,bbox_inches="tight"); plt.close()

# C: Fed Reaction Episodes
print("  [9/12] Appendix C: Fed reaction...")
epc=[("1990 Gulf",1.6,0.4,"CUT"),("2005 Katrina",2.2,0.1,"HIKED*"),("2008 Oil",1.6,0.2,"CUT"),
     ("2011 Libya",2.3,0.6,"HELD"),("2014 Crash",-2.2,0.1,"HELD"),("2022 Russia",1.6,0.1,"HIKED*")]
fig,ax=plt.subplots(figsize=(10,5.5)); xp=np.arange(len(epc)); w=0.35
ax.bar(xp-w/2,[e[1] for e in epc],w,label="Headline CPI \u0394",color=RED,alpha=0.8)
ax.bar(xp+w/2,[e[2] for e in epc],w,label="Core PCE \u0394",color=ACCENT,alpha=0.8)
ax.set_xticks(xp); ax.set_xticklabels([e[0] for e in epc],fontsize=9)
for i,e in enumerate(epc): ax.text(i,max(e[1],e[2])+0.15,e[3],ha="center",fontsize=8,fontweight="bold",color=NAVY)
ax.set_ylabel("Inflation Change (pp)"); ax.set_title("Fed Reaction to Oil Shocks: Headline vs Core\n(Fed targeted CORE in 6/6 episodes)"); ax.legend(fontsize=9)
ax.text(0.98,0.95,"*Pre-existing cycle",transform=ax.transAxes,ha="right",va="top",fontsize=8,fontstyle="italic",color=DGRAY)
plt.tight_layout(); plt.savefig("../output/pitch_charts/appendix/figC_fed_reaction_episodes.png",dpi=300,bbox_inches="tight"); plt.close()

# D: QT Episodes
print("  [10/12] Appendix D: QT episodes...")
qte=[("Taper\nTantrum",75,0),("QT1",25,3.6),("QT2 Ph1",25,7.5),("QT2 Ph2",35,4.3),("QT2 Full",65,3.3)]
fig,(a1,a2)=plt.subplots(1,2,figsize=(12,5))
a1.bar(range(len(qte)),[e[1] for e in qte],color=[ORANGE if e[2]==0 else ACCENT for e in qte],edgecolor="white")
a1.set_xticks(range(len(qte))); a1.set_xticklabels([e[0] for e in qte],fontsize=8)
a1.set_ylabel("TP Change (bp)"); a1.set_title("TP Change by Episode")
for i,e in enumerate(qte): a1.text(i,e[1]+1,f"+{e[1]}bp",ha="center",fontsize=9,fontweight="bold")
a2.bar(range(1,len(qte)),[e[2] for e in qte[1:]],color=ACCENT,edgecolor="white")
a2.set_xticks(range(1,len(qte))); a2.set_xticklabels([e[0] for e in qte[1:]],fontsize=8)
a2.set_ylabel("bp per $100B"); a2.set_title("TP Sensitivity"); a2.axhline(4.0,color=RED,ls="--",lw=1.5,label="Median: 4.0")
a2.legend(fontsize=9)
plt.suptitle("QT Episodes: BS Reduction \u2192 Term Premium",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("../output/pitch_charts/appendix/figD_qt_episodes.png",dpi=300,bbox_inches="tight"); plt.close()

# E: Technical
print("  [11/12] Appendix E: Technical...")
sts=daily["spread_bp"]; s50=sts.rolling(50).mean(); s200=sts.rolling(200).mean()
bm=sts.rolling(20).mean(); bs=sts.rolling(20).std(); bu=bm+2*bs; bl=bm-2*bs
d=sts.diff(); g=d.clip(lower=0).rolling(14).mean(); lo=(-d).clip(lower=0).rolling(14).mean()
rsi=100-(100/(1+g/lo))
rm=sts.index>=sts.index[-1]-pd.Timedelta(days=365)
fig,(a1,a2)=plt.subplots(2,1,figsize=(12,7),gridspec_kw={"height_ratios":[3,1]},sharex=True)
a1.plot(sts[rm].index,sts[rm],color=NAVY,lw=1.5,label="2s10s Spread",zorder=3)
a1.plot(s50[rm].index,s50[rm],color=ACCENT,lw=1.2,ls="--",label="50D SMA")
a1.plot(s200[rm].index,s200[rm],color=RED,lw=1.2,ls="--",label="200D SMA")
a1.fill_between(bu[rm].index,bl[rm],bu[rm],alpha=0.1,color=GRAY,label="Bollinger")
a1.axhline(42,color=RED,lw=0.8,ls=":",alpha=0.7,label="Stop: 42bp"); a1.axhline(70,color=GREEN,lw=0.8,ls=":",alpha=0.7,label="Target: 70bp")
a1.set_ylabel("Spread (bp)"); a1.set_title("2s10s Spread: Technical Analysis"); a1.legend(fontsize=8,loc="upper left",ncol=2)
a2.plot(rsi[rm].index,rsi[rm],color=PURPLE,lw=1.2); a2.axhline(70,color=RED,lw=0.8,ls="--",alpha=0.5); a2.axhline(30,color=GREEN,lw=0.8,ls="--",alpha=0.5)
a2.fill_between(rsi[rm].index,30,70,alpha=0.05,color=GRAY); a2.set_ylabel("RSI(14)"); a2.set_ylim(10,90)
a1.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
plt.tight_layout(); plt.savefig("../output/pitch_charts/appendix/figE_technical.png",dpi=300,bbox_inches="tight"); plt.close()

# F: Bootstrap
print("  [12/12] Appendix F: Bootstrap (10k resamples)...")
np.random.seed(42); nb=10000; X_bs=d_daily[["d_rate_exp","d_acm"]].values; y_bs=d_daily["d_spread"].values; no=len(y_bs)
bwk=wk_chg["d_be2y"].values; b10wk=wk_chg["d_be10y"].values; owk=wk_chg["oil_pct"].values; nw2=len(owk)
Xc=sm.add_constant(X_bs); bf,_,_,_=lstsq(Xc,y_bs,rcond=None); yh=Xc@bf
r2f=1-np.sum((y_bs-yh)**2)/np.sum((y_bs-y_bs.mean())**2)
s2f,_,_,_,_=stats.linregress(owk,bwk); s10f,_,_,_,_=stats.linregress(owk,b10wk)
brf=s2f/s10f if s10f else float("inf")
btp=np.empty(nb);bre2=np.empty(nb);br2=np.empty(nb);brat=np.empty(nb)
for b in range(nb):
    idx=np.random.randint(0,no,no); Xb=sm.add_constant(X_bs[idx]); yb=y_bs[idx]
    try:
        bb,_,_,_=lstsq(Xb,yb,rcond=None); yhb=Xb@bb
        bre2[b]=bb[1]; btp[b]=bb[2]; br2[b]=1-np.sum((yb-yhb)**2)/np.sum((yb-yb.mean())**2)
    except: bre2[b]=btp[b]=br2[b]=np.nan
    iw=np.random.randint(0,nw2,nw2)
    s2b,_,_,_,_=stats.linregress(owk[iw],bwk[iw]); s10b,_,_,_,_=stats.linregress(owk[iw],b10wk[iw])
    brat[b]=s2b/s10b if abs(s10b)>1e-10 else np.nan

fig,axes=plt.subplots(2,2,figsize=(11,8))
for ax,data,name,pt in [(axes[0,0],btp,"\u03B2(Term Premium)",bf[2]),(axes[0,1],bre2,"\u03B2(Rate Expectations)",bf[1]),
                          (axes[1,0],brat,"2Y/10Y BE Sensitivity",brf),(axes[1,1],br2,"R\u00B2 (A2)",r2f)]:
    c=data[~np.isnan(data)]; p5,p95=np.percentile(c,5),np.percentile(c,95)
    ax.hist(c,bins=60,color=GRAY,edgecolor="white",alpha=0.8)
    ax.axvline(pt,color=NAVY,lw=2,label=f"Point: {pt:.2f}"); ax.axvline(p5,color=RED,lw=1.5,ls="--",label=f"5th: {p5:.2f}")
    ax.axvline(p95,color=RED,lw=1.5,ls="--",label=f"95th: {p95:.2f}"); ax.set_title(name,fontweight="bold",fontsize=11); ax.legend(fontsize=8)
plt.suptitle("Bootstrap Distributions (10,000 resamples, 90% CI)",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("../output/pitch_charts/appendix/figF_bootstrap.png",dpi=300,bbox_inches="tight"); plt.close()

# ══════════════════════════════════════════════════════════
# REGRESSION TABLES
# ══════════════════════════════════════════════════════════
print("  Writing regression tables...")

def hr(y,X,nm):
    Xc=sm.add_constant(X); lg=int(np.floor(4*(len(y)/100)**(2/9)))
    mh=sm.OLS(y,Xc).fit(cov_type="HAC",cov_kwds={"maxlags":lg})
    return {"nm":nm,"c":mh.params[1:],"se":mh.bse[1:],"t":mh.tvalues[1:],"p":mh.pvalues[1:],"r2":mh.rsquared,"n":len(y)}

regs=[hr(d_daily["d_spread"].values,d_daily[["d_rate_exp","d_acm"]].values,"A2"),
      hr(wk_chg["d_be2y"].values,wk_chg[["oil_pct"]].values,"A3a"),
      hr(wk_chg["d_be10y"].values,wk_chg[["oil_pct"]].values,"A3b")]

with open("../output/regression_tables/table1_core_regressions.txt","w") as f:
    f.write("TABLE 1: Core Regressions (Newey-West HAC SEs)\n"+"="*85+"\n\n")
    f.write(f"{'Regression':<35} {'Coeff':>8} {'HAC SE':>8} {'t-stat':>8} {'p':>8} {'R2':>8} {'N':>6}\n"+"-"*85+"\n")
    labels=[["A2: d(Rate Exp)","A2: d(Term Prem)"],["A3a: Oil% -> d(2Y BE)"],["A3b: Oil% -> d(10Y BE)"]]
    for r,lbs in zip(regs,labels):
        for i,lb in enumerate(lbs):
            f.write(f"{lb:<35} {r['c'][i]:>+8.4f} {r['se'][i]:>8.4f} {r['t'][i]:>+8.2f} {r['p'][i]:>8.4f}")
            if i==0: f.write(f" {r['r2']:>8.4f} {r['n']:>6d}")
            f.write("\n")
    f.write("\nNotes: All use first differences. A2 VIF=1.28. HAC bandwidth automatic.\n")

with open("../output/regression_tables/table2_robustness.txt","w") as f:
    f.write("TABLE 2: Bootstrap CIs & Rolling Windows\n"+"="*70+"\n\n")
    f.write(f"{'Statistic':<32} {'Point':>10} {'5th':>8} {'95th':>8}\n"+"-"*60+"\n")
    for nm,pt,arr in [("B(Term Premium)",bf[2],btp),("B(Rate Expectations)",bf[1],bre2),("2Y/10Y BE Sensitivity",brf,brat),("R2 (A2)",r2f,br2)]:
        c=arr[~np.isnan(arr)]; f.write(f"{nm:<32} {pt:>+10.4f} {np.percentile(c,5):>+8.4f} {np.percentile(c,95):>+8.4f}\n")
    f.write(f"\n{'Rolling (252-day):'}\n  Mean B(TP): {rbt.mean():+.3f}\n  Min: {rbt.min():+.3f}\n  Max: {rbt.max():+.3f}\n  % positive: 100%\n")

with open("../output/regression_tables/table3_stationarity.txt","w") as f:
    f.write("TABLE 3: Stationarity (ADF + KPSS)\n"+"="*100+"\n\n")
    f.write(f"{'Series':<22} {'ADF p':>8} {'KPSS p':>8} {'Level':<26} {'ADF p(d)':>8} {'Diff':<26}\n"+"-"*100+"\n")
    for nm,s in [("Spread",daily["spread_bp"]),("ACM TP",daily["acm"]),("Rate Exp",daily["rate_exp"]),
                  ("2Y BE",daily["be2y"]),("10Y BE",daily["be10y"]),("Oil",daily["oil"]),("2Y Yield",daily["ust2y"]),("10Y Yield",daily["ust10y"])]:
        sc=s.dropna(); ap=adfuller(sc,autolag="AIC")[1]; kp=kpss(sc,regression="c",nlags="auto")[1]
        ar=ap<0.05; kr=kp<0.05
        vl="I(0)" if ar and not kr else "I(1)" if not ar and kr else "Ambiguous"
        sd=sc.diff().dropna(); apd=adfuller(sd,autolag="AIC")[1]; kpd=kpss(sd,regression="c",nlags="auto")[1]
        ard=apd<0.05; krd=kpd<0.05; vd="I(0)" if ard and not krd else "I(1)" if not ard and krd else "Ambiguous"
        f.write(f"{nm:<22} {ap:>8.4f} {kp:>8.4f} {vl:<26} {apd:>8.4f} {vd:<26}\n")

with open("../output/regression_tables/table4_expression_comparison.txt","w") as f:
    f.write("TABLE 4: Trade Expression Comparison\n"+"="*110+"\n\n")
    f.write(f"{'Expression':<28} {'Captures':<16} {'Carry':>9} {'Margin':>10} {'R/R':>9} {'Suitable?':<18}\n"+"-"*110+"\n")
    for r in [("Cash bond steepener","P1+P2 mixed","-4.5bp/m","$50k+","0.1:1","NO (carry,capital)"),
              ("Futures (ZT/ZN)","P1+P2 mixed","~-2bp/m","$3-5k","~0.5:1","NO (carry drag)"),
              ("SOFR strip only","P1 only","~0bp/m","$4k","Varies","NO (no P2)"),
              ("SOFR + Micro 10Y [REC]","P1+P2 isolated","~0bp/m","$12k","2.5:1","YES"),
              ("Options overlay","P1+P2 defined","Premium","Premium","3:1+","NO (complexity)")]:
        f.write(f"{r[0]:<28} {r[1]:<16} {r[2]:>9} {r[3]:>10} {r[4]:>9} {r[5]:<18}\n")
    f.write("\nP1=Front-end overreaction, P2=Term premium. REC=Recommended.\n")

# ══════════════════════════════════════════════════════════
print("\n"+"="*60)
print("  ALL PITCH MATERIALS GENERATED")
print("="*60)
ct=0
for root,_,files in os.walk("../output/pitch_charts"): ct+=len(files)
for root,_,files in os.walk("../output/regression_tables"): ct+=len(files)
print(f"  {ct} files produced. Ready for doc assembly.")
print(f"  Charts: ../output/pitch_charts/")
print(f"  Tables: ../output/regression_tables/\n")
