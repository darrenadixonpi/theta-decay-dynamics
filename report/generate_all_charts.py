"""
Consolidated chart generation for Theta Decay Dynamics Report v4.4+.
"""
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from options_math import *

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUTDIR, exist_ok=True)
r_rate = 0.05; K = 100.0
PAL = ['#2563EB','#DC2626','#F59E0B','#10B981','#8B5CF6','#EC4899']
plt.rcParams.update({'figure.facecolor':'#FAFAFA','axes.facecolor':'#FFFFFF','axes.edgecolor':'#D1D5DB',
    'axes.labelcolor':'#1F2937','axes.labelsize':10,'axes.titlesize':11,'axes.titleweight':'bold',
    'axes.grid':True,'grid.color':'#E5E7EB','grid.linewidth':0.5,'grid.alpha':0.7,
    'xtick.color':'#1F2937','ytick.color':'#1F2937','xtick.labelsize':9,'ytick.labelsize':9,
    'legend.fontsize':8,'legend.framealpha':0.9,'legend.edgecolor':'#D1D5DB',
    'font.size':9,'lines.linewidth':1.8,'figure.dpi':180,'savefig.dpi':180,
    'savefig.bbox':'tight','savefig.pad_inches':0.15})
def save(fig, name): fig.savefig(f'{OUTDIR}/{name}.png'); plt.close(fig); print(f'  {name}')

def fig01():
    fig,ax=plt.subplots(figsize=(8,6)); dtes=np.arange(1,181)
    for i,(m,l) in enumerate([(1.00,'ATM (S/K=1.00)'),(1.05,'S/K=1.05'),(1.10,'S/K=1.10'),(1.20,'S/K=1.20'),(1.40,'S/K=1.40'),(0.90,'S/K=0.90 (ITM)')]):
        ax.plot(dtes[::-1],[short_put_theta(m*K,K,r_rate,0.80,d/365) for d in dtes],color=PAL[i],label=l)
    ax.set_xlabel('Days to Expiry');ax.set_ylabel('Daily Theta Collected ($/share)')
    ax.set_title('Short Put: Theta vs DTE by Moneyness (\u03c3 = 80%)');ax.set_xlim(180,0);ax.legend();save(fig,'fig01_put_moneyness')

def fig02():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,181);S=1.30*K
    for i,iv in enumerate([0.40,0.60,0.80,1.20,1.80,2.50]):
        ax.plot(dtes[::-1],[short_put_theta(S,K,r_rate,iv,d/365) for d in dtes],color=PAL[i%6],label=f'IV={int(iv*100)}%')
    ax.set_xlabel('Days to Expiry');ax.set_ylabel('Daily Theta ($/share)')
    ax.set_title('Short Put IV Effect: S/K = 1.30, K = $100');ax.set_xlim(180,0);ax.legend();save(fig,'fig02_put_iv')

def fig03():
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5));dtes=np.arange(1,181)
    for ax,S,t in [(a1,1.30*K,'OTM (S/K = 1.30)'),(a2,K,'ATM (S/K = 1.00)')]:
        for iv,ls,c in [(0.60,'-',PAL[0]),(1.20,'--',PAL[1])]:
            ax.plot(dtes[::-1],[short_put_theta(S,K,r_rate,iv,d/365) for d in dtes],ls,color=c,label=f'IV={int(iv*100)}%')
        ax.set_title(t);ax.set_xlabel('DTE');ax.set_ylabel('Theta ($/day)');ax.legend();ax.set_xlim(180,0)
    fig.suptitle('IV Shock Asymmetry: OTM vs ATM Short Puts',fontsize=12,fontweight='bold',y=1.02);fig.tight_layout();save(fig,'fig03_put_iv_shock')

def fig04():
    fig=plt.figure(figsize=(7.5,7));ax=fig.add_subplot(111,projection='3d')
    sk=np.linspace(0.80,1.50,45);dtes=np.linspace(1,120,45);SK,DTE=np.meshgrid(sk,dtes)
    Z=np.vectorize(lambda s,d:short_put_theta(s*K,K,r_rate,0.80,d/365))(SK,DTE)
    ax.plot_surface(SK,DTE,Z,cmap='viridis',alpha=0.88,edgecolor='none')
    ax.set_xlabel('S/K',labelpad=10);ax.set_ylabel('DTE',labelpad=10);ax.set_zlabel('Theta',labelpad=8)
    ax.set_title('Short Put Theta Surface (\u03c3 = 80%)',pad=15);ax.view_init(elev=28,azim=225);save(fig,'fig04_put_surface')

def fig05():
    fig,ax=plt.subplots(figsize=(8,6));sk=np.linspace(1.01,1.80,100)
    for i,sig in enumerate([0.40,0.60,0.80,1.20,1.50,2.00]):
        ax.plot(sk,[theta_peak_dte(s*K,K,sig) for s in sk],color=PAL[i%6],label=f'\u03c3={int(sig*100)}%')
    ax.set_xlabel('Moneyness (S/K)');ax.set_ylabel('DTE at Theta Peak')
    ax.set_title('Peak Theta Timing vs Moneyness & Volatility');ax.legend();save(fig,'fig05_peak_timing')

def fig06():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,181)
    for i,(m,l) in enumerate([(1.00,'ATM'),(0.95,'S/K=0.95 (OTM)'),(0.90,'S/K=0.90'),(0.80,'S/K=0.80'),(0.70,'S/K=0.70'),(1.10,'S/K=1.10 (ITM)')]):
        ax.plot(dtes[::-1],[short_call_theta(m*K,K,r_rate,0.80,d/365) for d in dtes],color=PAL[i],label=l)
    ax.set_xlabel('DTE');ax.set_ylabel('Daily Theta ($/share)');ax.set_title('Short Call: Theta vs DTE by Moneyness (\u03c3 = 80%)')
    ax.set_xlim(180,0);ax.legend();save(fig,'fig06_call_moneyness')

def fig07():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,181)
    for i,(sk,l) in enumerate([(1.00,'ATM (S=K)'),(1.05,'S/K=1.05'),(1.10,'S/K=1.10'),(1.20,'S/K=1.20'),(0.90,'S/K=0.90'),(0.80,'S/K=0.80')]):
        S=sk*K;ax.plot(dtes[::-1],[short_put_theta(S,K,r_rate,0.80,d/365)+short_call_theta(S,K,r_rate,0.80,d/365) for d in dtes],color=PAL[i],label=l)
    ax.set_xlabel('DTE');ax.set_ylabel('Daily Theta ($/share)');ax.set_title('Short Straddle: Theta vs DTE (\u03c3 = 80%)')
    ax.set_xlim(180,0);ax.legend();save(fig,'fig07_straddle')

def fig08():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,181);S=100.0
    for w,c in [(5,PAL[0]),(10,PAL[1]),(20,PAL[2]),(30,PAL[3])]:
        ax.plot(dtes[::-1],[short_put_theta(S,K-w,r_rate,0.80,d/365)+short_call_theta(S,K+w,r_rate,0.80,d/365) for d in dtes],color=c,label=f'\u00b1{w} ({int(K-w)}P/{int(K+w)}C)')
    ax.plot(dtes[::-1],[short_put_theta(S,K,r_rate,0.80,d/365)+short_call_theta(S,K,r_rate,0.80,d/365) for d in dtes],'--',color=PAL[4],label='Straddle (ref)')
    ax.set_xlabel('DTE');ax.set_ylabel('Daily Theta ($/share)');ax.set_title('Short Strangle: Theta by Wing Width (\u03c3 = 80%, S = $100)')
    ax.set_xlim(180,0);ax.legend();save(fig,'fig08_strangle')

def fig09():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,181);S=105.0;Ks=100.0
    for i,w in enumerate([5,10,20,30]):
        ax.plot(dtes[::-1],[short_put_theta(S,Ks,r_rate,0.80,d/365)-short_put_theta(S,Ks-w,r_rate,0.80,d/365) for d in dtes],color=PAL[i],label=f'${w} wide ({int(Ks)}P/{int(Ks-w)}P)')
    ax.plot(dtes[::-1],[short_put_theta(S,Ks,r_rate,0.80,d/365) for d in dtes],'--',color=PAL[4],label='Naked 100P (ref)')
    ax.set_xlabel('DTE');ax.set_ylabel('Daily Net Theta ($/share)');ax.set_title(f'Bull Put Spread: Net Theta by Width (S=${int(S)}, \u03c3 = 80%)')
    ax.set_xlim(180,0);ax.legend();save(fig,'fig09_credit_spread')

def fig10():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,181);S=100.0
    for i,(l,Kpl,Kps,Kcs,Kcl) in enumerate([('Narrow: 85P/95P/105C/115C',85,95,105,115),('Medium: 80P/90P/110C/120C',80,90,110,120),('Wide: 70P/80P/120C/130C',70,80,120,130)]):
        ax.plot(dtes[::-1],[short_put_theta(S,Kps,r_rate,0.80,d/365)-short_put_theta(S,Kpl,r_rate,0.80,d/365)+short_call_theta(S,Kcs,r_rate,0.80,d/365)-short_call_theta(S,Kcl,r_rate,0.80,d/365) for d in dtes],color=PAL[i],label=l)
    ax.set_xlabel('DTE');ax.set_ylabel('Daily Net Theta ($/share)');ax.set_title('Iron Condor: Net Theta by Configuration (\u03c3 = 80%, S = $100)')
    ax.set_xlim(180,0);ax.legend();save(fig,'fig10_iron_condor')

def fig11():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,46)
    t1=np.array([short_put_theta(50,50,r_rate,0.35,d/365)*100 for d in dtes])
    t2=np.array([(short_put_theta(100,80,r_rate,0.90,d/365)+short_call_theta(100,120,r_rate,0.90,d/365))*100 for d in dtes])
    t3=np.array([(short_put_theta(105,95,r_rate,1.10,d/365)-short_put_theta(105,85,r_rate,1.10,d/365))*100 for d in dtes])
    t4=np.array([short_put_theta(52,40,r_rate,0.55,d/365)*100 for d in dtes])
    x=dtes[::-1]
    ax.stackplot(x,t1,t2,t3,t4,colors=[PAL[0],PAL[2],PAL[3],PAL[4]],alpha=0.75,
                 labels=['ATM CSP ($50P, IV=35%)','OTM Strangle (80P/120C, IV=90%)','Credit Spread (95P/85P, IV=110%)','OTM CSP ($40P, IV=55%)'])
    ax.plot(x,t1+t2+t3+t4,'k-',linewidth=1.5,label='Net Total')
    ax.set_xlabel('Days to Expiry');ax.set_ylabel('Daily Theta ($/day per contract)')
    ax.set_title('Portfolio Theta Aggregation: 4 Positions Over 45 DTE');ax.set_xlim(45,0);ax.legend(fontsize=7,loc='upper left');save(fig,'fig11_portfolio')

def fig_sens_grid():
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5));sk=np.linspace(1.02,1.50,50)
    for i,iv in enumerate([0.15,0.30,0.60,1.00]):
        a1.plot(sk,[theta_peak_dte(s*K,K,iv) for s in sk],color=PAL[i],label=f'IV={int(iv*100)}%')
    a1.set_xlabel('Moneyness (S/K)');a1.set_ylabel('Peak Theta DTE');a1.set_title('T* Peak Timing Across IV Levels');a1.legend();a1.set_ylim(0,400)
    sk2=np.linspace(1.0,1.30,30)
    for i,rate in enumerate([0.01,0.03,0.05,0.08]):
        a2.plot(sk2,[sum(short_put_theta(s*K,K,rate,0.30,d/365) for d in range(1,46)) for s in sk2],color=PAL[i],label=f'r={int(rate*100)}%')
    a2.set_xlabel('Moneyness (S/K)');a2.set_ylabel('Total Theta ($/share, 45 DTE)');a2.set_title('Rate Sensitivity');a2.legend()
    fig.suptitle('Parameter Sensitivity: T* and Total Theta',fontsize=11,fontweight='bold');fig.tight_layout(rect=[0,0,1,0.96]);save(fig,'fig_sens_grid')

def fig_skew():
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5));dtes=np.arange(1,91);S=100
    a1.plot(dtes[::-1],[short_put_theta(S,90,r_rate,0.25,d/365) for d in dtes],color=PAL[0],label='Flat IV = 25%')
    a1.plot(dtes[::-1],[short_put_theta(S,90,r_rate,0.35,d/365) for d in dtes],color=PAL[1],label='Skewed IV = 35%')
    a1.set_title('OTM Put (K=$90): Flat vs Skewed IV');a1.set_xlabel('DTE');a1.set_ylabel('Theta ($/day)');a1.legend(fontsize=7);a1.set_xlim(90,0)
    a2.plot(dtes[::-1],[short_put_theta(S,90,r_rate,0.25,d/365)+short_call_theta(S,110,r_rate,0.25,d/365) for d in dtes],color=PAL[0],label='Flat IV = 25% both legs')
    a2.plot(dtes[::-1],[short_put_theta(S,90,r_rate,0.32,d/365)+short_call_theta(S,110,r_rate,0.20,d/365) for d in dtes],color=PAL[1],label='Skewed: put 32% / call 20%')
    a2.set_title('Strangle (90P/110C): Flat vs Skewed IV');a2.set_xlabel('DTE');a2.set_ylabel('Theta ($/day)');a2.legend(fontsize=7);a2.set_xlim(90,0)
    fig.suptitle('Volatility Skew Impact on Theta Profiles',fontsize=11,fontweight='bold');fig.tight_layout(rect=[0,0,1,0.96]);save(fig,'fig_skew')

def fig_merton():
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5));dtes=np.arange(1,181)
    for ax,S,t in [(a1,K,'ATM (S/K = 1.00)'),(a2,1.30*K,'OTM (S/K = 1.30)')]:
        ax.plot(dtes[::-1],[short_put_theta(S,K,r_rate,0.59,d/365) for d in dtes],color=PAL[0],label='BS (\u03c3=59%)')
        ax.plot(dtes[::-1],[short_put_theta_merton(S,K,r_rate,0.35,d/365,2.5,0.0,0.20) for d in dtes],'--',color=PAL[1],label='Merton (\u03c3d=35%, \u03bb=2.5)')
        ax.set_title(t);ax.set_xlabel('DTE');ax.set_ylabel('Theta ($/day)');ax.legend();ax.set_xlim(180,0)
    fig.suptitle('Merton vs Black-Scholes Theta',fontsize=12,fontweight='bold',y=1.02);fig.tight_layout();save(fig,'fig_merton')

def fig_costs():
    fig,ax=plt.subplots(figsize=(8,6));dtes=np.arange(1,46);S=105;Ks=100;sigma=0.80
    gross=np.array([short_put_theta(S,Ks,r_rate,sigma,d/365)*100 for d in dtes])
    prem=bs_put_price(S,Ks,r_rate,sigma,45/365)
    ax.plot(dtes[::-1],gross,color=PAL[4],lw=2.2,label='Gross Theta')
    for l,sp_,comm,c in [('Retail (3%, $0.65)',0.03,0.65,PAL[1]),('Active (2%, $0.50)',0.02,0.50,PAL[3]),('Institutional (1%, $0.10)',0.01,0.10,PAL[0])]:
        ax.plot(dtes[::-1],gross-compute_transaction_costs(prem,sp_,1,comm)/45,'--',color=c,lw=1.5,label=l)
    ax.set_xlabel('Days to Expiry');ax.set_ylabel('Daily Theta ($/day)');ax.set_title('Net Theta After Transaction Costs')
    ax.set_xlim(45,0);ax.axhline(0,color='#9CA3AF',lw=0.5);ax.legend();save(fig,'fig_costs')

def fig_risk():
    fig,ax=plt.subplots(figsize=(8,6));np.random.seed(123);S0=100;sigma=0.30;T_d=45;n=5000
    ta=[];es=[]
    for sk in [1.00,1.05,1.10,1.15,1.20]:
        Kp=S0/sk;prem=bs_put_price(S0,Kp,r_rate,sigma,T_d/365)
        finals=S0*np.exp((r_rate-0.5*sigma**2)*T_d/252+sigma*np.sqrt(T_d/252)*np.random.standard_normal(n))
        pnls=(prem-np.maximum(Kp-finals,0))*100
        ta.append(sum(short_put_theta(S0,Kp,r_rate,sigma,d/365) for d in range(1,T_d+1))/T_d)
        es.append(-np.mean(pnls[pnls<=np.percentile(pnls,5)]))
    ax.scatter(es,ta,s=120,c=PAL[:5],zorder=5,edgecolors='white',linewidth=1.5)
    for i,sk in enumerate([1.00,1.05,1.10,1.15,1.20]):
        ax.annotate(f'S/K={sk:.2f}',(es[i],ta[i]),textcoords='offset points',xytext=(8,5),fontsize=9)
    ax.set_xlabel('Expected Shortfall 5% ($/contract)');ax.set_ylabel('Average Daily Theta ($/share)')
    ax.set_title('Theta\u2013Risk Frontier by Moneyness (45 DTE, \u03c3 = 30%)');save(fig,'fig_risk')

def fig_regime():
    fig,axes=plt.subplots(2,2,figsize=(10,7.5));np.random.seed(42)
    regs=[('Low Vol (\u03c3=15%)',0.15,0.02,0,0,0),('Normal (\u03c3=20%)',0.20,0.04,0,0,0),('Elevated (\u03c3=35%)',0.35,-0.02,0,0,0),('Crisis (\u03c3=50%)',0.50,-0.10,3.0,-0.05,0.15)]
    for idx,(nm,sig,dr,lam,mj,sj) in enumerate(regs):
        ax=axes[idx//2][idx%2];tm=np.zeros((1500,45))
        for p in range(1500):
            S=100;dt_=1/252
            for d in range(45):
                Tr=(45-d)/365
                if Tr<=0:break
                tm[p,d]=short_put_theta(S,90,r_rate,sig,Tr)
                z=np.random.standard_normal();dS=S*((r_rate+dr)*dt_+sig*np.sqrt(dt_)*z)
                if lam>0:
                    for _ in range(np.random.poisson(lam*dt_)):dS+=S*(np.exp(mj+sj*np.random.standard_normal())-1)
                S=max(S+dS,0.01)
        med=np.median(tm,axis=0);p25=np.percentile(tm,25,axis=0);p75=np.percentile(tm,75,axis=0);x=np.arange(45,0,-1)
        ax.fill_between(x,p25,p75,alpha=0.25,color=PAL[0]);ax.plot(x,med,color=PAL[0],lw=2)
        ax.set_title(nm);ax.set_xlabel('DTE');ax.set_ylabel('Theta ($/day)');ax.set_xlim(45,0)
        total=np.sum(med);first=np.sum(med[:22])
        ax.text(0.96,0.94,f'Total: ${total:.1f}\n1st half: {first/total*100:.0f}%',transform=ax.transAxes,ha='right',va='top',fontsize=8,bbox=dict(boxstyle='round,pad=0.3',fc='white',ec='#D1D5DB',alpha=0.9))
    fig.suptitle('Regime Analysis: OTM Short Put (S/K = 1.11) \u2014 1,500 paths per regime',fontsize=11,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,0.96]);save(fig,'fig_regime')

def _run_trade(S0,strat,iv,rv,dte,managed=False):
    dt_=1/252;Kp=95;Kc=110;Ks=95;Kl=90
    if strat=='csp':margin=Kp*100;prem=bs_put_price(S0,Kp,r_rate,iv,dte/365)*100
    elif strat=='strangle':margin=max(90,110)*100+500;prem=(bs_put_price(S0,90,r_rate,iv,dte/365)+bs_call_price(S0,110,r_rate,iv,dte/365))*100
    elif strat=='spread':margin=500;prem=(bs_put_price(S0,95,r_rate,iv,dte/365)-bs_put_price(S0,90,r_rate,iv,dte/365))*100
    S=S0
    for d in range(dte):
        Tr=(dte-d)/365
        if Tr<=1e-6:break
        if managed:
            if strat=='csp':cur=bs_put_price(S,95,r_rate,iv,Tr)*100
            elif strat=='strangle':cur=(bs_put_price(S,90,r_rate,iv,Tr)+bs_call_price(S,110,r_rate,iv,Tr))*100
            elif strat=='spread':cur=(bs_put_price(S,95,r_rate,iv,Tr)-bs_put_price(S,90,r_rate,iv,Tr))*100
            if prem>0 and(prem-cur)/prem>=0.50:return prem-cur,margin
            if(dte-d)<=21:return prem-cur,margin
        S=S*np.exp((r_rate-0.5*rv**2)*dt_+rv*np.sqrt(dt_)*np.random.standard_normal())
    if strat=='csp':payoff=max(95-S,0)*100
    elif strat=='strangle':payoff=(max(90-S,0)+max(S-110,0))*100
    elif strat=='spread':payoff=(max(95-S,0)-max(90-S,0))*100
    return prem-payoff,margin

def fig_risk_multi():
    np.random.seed(42);strats=[('OTM CSP hold','csp',False),('OTM CSP managed','csp',True),('Strangle hold','strangle',False),('Strangle managed','strangle',True),('Credit Spread hold','spread',False),('Credit Spread managed','spread',True)]
    ad={}
    for nm,st,mg in strats:
        ps=[];ms=[]
        for _ in range(200):p,m=_run_trade(100,st,0.25,0.18,45,mg);ps.append(p);ms.append(m)
        ad[nm]={'pnls':np.array(ps),'margin':np.mean(ms)}
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5))
    for i,(nm,st,mg) in enumerate(strats):
        eq=np.cumsum(ad[nm]['pnls']);ls='-' if not mg else '--';ci=i//2
        a1.plot(eq,color=PAL[ci],ls=ls,lw=1.3,label=nm,alpha=0.9 if not mg else 0.7)
        pk=np.maximum.accumulate(eq);a2.plot(-(pk-eq),color=PAL[ci],ls=ls,lw=1.2,label=nm,alpha=0.9 if not mg else 0.7)
    a1.set_xlabel('Trade #');a1.set_ylabel('Cumulative P&L ($)');a1.set_title('Equity Curves (200 trades)');a1.legend(fontsize=6.5);a1.axhline(0,color='#9CA3AF',lw=0.5)
    a2.set_xlabel('Trade #');a2.set_ylabel('Drawdown ($)');a2.set_title('Drawdown Paths');a2.legend(fontsize=6.5)
    fig.suptitle('Multi-Structure Risk: CSP vs Strangle vs Credit Spread',fontsize=10,fontweight='bold',y=1.01);fig.tight_layout();save(fig,'fig_risk_equity')
    fig,axes=plt.subplots(1,3,figsize=(11,3.5))
    for idx,(title,hn,mn) in enumerate([('OTM CSP','OTM CSP hold','OTM CSP managed'),('Strangle','Strangle hold','Strangle managed'),('Credit Spread','Credit Spread hold','Credit Spread managed')]):
        ax=axes[idx]
        for nm,clr,lb in [(hn,PAL[0],'Hold'),(mn,PAL[3],'Managed')]:
            ls=ad[nm]['pnls']<0;runs=[];cur=0
            for l in ls:
                if l:cur+=1
                else:
                    if cur>0:runs.append(cur)
                    cur=0
            if cur>0:runs.append(cur)
            if runs:ax.hist(runs,bins=np.arange(0.5,max(max(runs),6)+1.5,1),alpha=0.6,color=clr,label=lb,density=True,edgecolor='white')
        ax.set_xlabel('Consecutive Losses');ax.set_ylabel('Frequency');ax.set_title(title);ax.legend(fontsize=7);ax.set_xlim(0.5,6.5)
    fig.suptitle('Loss Clustering by Structure (Small Multiples)',fontsize=10,fontweight='bold');fig.tight_layout(rect=[0,0,1,0.94]);save(fig,'fig_risk_clustering')
    fig,ax=plt.subplots(figsize=(8,5))
    data=[ad[s[0]]['pnls'] for s in strats];labels=[s[0].replace(' ','\n') for s in strats]
    bp=ax.boxplot(data,tick_labels=labels,patch_artist=True,widths=0.55,medianprops=dict(color='#1F2937',lw=2),whiskerprops=dict(color='#6B7280'),capprops=dict(color='#6B7280'),flierprops=dict(marker='o',markersize=3,alpha=0.3))
    cols=[PAL[0],PAL[0],PAL[1],PAL[1],PAL[2],PAL[2]]
    for i,patch in enumerate(bp['boxes']):patch.set_facecolor(cols[i]+'33');patch.set_edgecolor(cols[i])
    ax.axhline(0,color='#9CA3AF',lw=0.5);ax.set_ylabel('Per-Trade P&L ($)');ax.set_title('P&L Distribution & Skew by Structure');ax.tick_params(axis='x',labelsize=7);save(fig,'fig_risk_boxplots')

def fig_sweep():
    np.random.seed(42);S0=100;Kp=95;iv=0.25;rv=0.18;n=400;dt_=1/252
    des=[30,35,40,45,50,55,60];tgts=[0.25,0.50,0.75,1.00];tl=['25%','50%','75%','Hold']
    sr=np.zeros((len(des),len(tgts)));wr=np.zeros_like(sr)
    for i,dte in enumerate(des):
        prem=bs_put_price(S0,Kp,r_rate,iv,dte/365)*100
        for j,tgt in enumerate(tgts):
            fl=21 if tgt<1.0 else 0;pnls=[];hd=[]
            for _ in range(n):
                S=S0;iv0=prem;cl=False
                for d in range(dte):
                    Tr=(dte-d)/365
                    if Tr<=1e-6:break
                    cur=bs_put_price(S,Kp,r_rate,iv,Tr)*100;pct=(iv0-cur)/iv0 if iv0>0 else 0
                    if tgt<1 and pct>=tgt:pnls.append(iv0-cur);hd.append(d+1);cl=True;break
                    if fl>0 and(dte-d)<=fl:pnls.append(iv0-cur);hd.append(d+1);cl=True;break
                    S=S*np.exp((r_rate-0.5*rv**2)*dt_+rv*np.sqrt(dt_)*np.random.standard_normal())
                if not cl:pnls.append(iv0-max(Kp-S,0)*100);hd.append(dte)
            pnls=np.array(pnls);ah=np.mean(hd);tpy=252/ah;ar=np.mean(pnls)*tpy;av=np.std(pnls)*np.sqrt(tpy)
            sr[i,j]=ar/av if av>0 else 0;wr[i,j]=np.mean(pnls>0)*100
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5.5))
    for ax,data,title,fmt,vmin in [(a1,sr,'Sharpe Ratio','.2f',0),(a2,wr,'Win Rate (%)','.0f',60)]:
        im=ax.imshow(data,cmap='RdYlGn',aspect='equal',vmin=vmin,extent=[-0.5,len(tgts)-0.5,len(des)-0.5,-0.5])
        for ii in range(len(des)):
            for jj in range(len(tgts)):ax.text(jj,ii,f'{data[ii,jj]:{fmt}}',ha='center',va='center',fontsize=9,fontweight='bold')
        ax.set_xticks(range(len(tgts)));ax.set_xticklabels(tl);ax.set_yticks(range(len(des)));ax.set_yticklabels([str(d) for d in des])
        ax.set_xlabel('Profit Target');ax.set_ylabel('Entry DTE');ax.set_title(title);plt.colorbar(im,ax=ax,shrink=0.75,pad=0.02)
    fig.suptitle('DTE \u00d7 Profit Target Sweep (IV=25%, RV=18%, 400 paths/cell)',fontsize=11,fontweight='bold',y=1.01);fig.tight_layout();save(fig,'fig_sweep')

def fig_dte_ci():
    np.random.seed(77);dt_=1/252;dte_range=np.arange(25,70,2);meds=[];lo=[];hi=[]
    for dte in dte_range:
        prem=bs_put_price(100,95,r_rate,0.25,dte/365)*100;pnls=[]
        for _ in range(300):
            S=100
            for d in range(dte):S=S*np.exp((r_rate-0.5*0.18**2)*dt_+0.18*np.sqrt(dt_)*np.random.standard_normal())
            pnls.append(prem-max(95-S,0)*100)
        pnls=np.array(pnls)
        boot=[]
        for _ in range(100):
            s=np.random.choice(pnls,len(pnls),True)
            boot.append(np.mean(s)*252/dte/(np.std(s)*np.sqrt(252/dte)) if np.std(s)>0 else 0)
        meds.append(np.median(boot));lo.append(np.percentile(boot,10));hi.append(np.percentile(boot,90))
    fig,ax=plt.subplots(figsize=(8,6))
    ax.fill_between(dte_range,lo,hi,alpha=0.2,color=PAL[0],label='80% bootstrap CI')
    ax.plot(dte_range,meds,color=PAL[0],lw=2,label='Median Sharpe');ax.axvspan(38,55,alpha=0.08,color=PAL[3],label='Competitive zone')
    ax.axhline(0,color='#9CA3AF',lw=0.5);ax.set_xlabel('Entry DTE');ax.set_ylabel('Simulated Sharpe Ratio')
    ax.set_title('Sharpe Ratio by Entry DTE with Bootstrap CI');ax.legend();save(fig,'fig_dte_ci')

def fig_sensitivity():
    fig,axes=plt.subplots(1,3,figsize=(12,4.5));Kp=90;dte=45
    sigs=np.linspace(0.15,0.60,20);sks=np.linspace(1.0,1.40,20)
    axes[0].plot(sigs*100,[sum(short_put_theta(100,Kp,r_rate,s,d/365) for d in range(1,dte+1)) for s in sigs],color=PAL[0],marker='o',markersize=3)
    axes[0].axvline(30,color=PAL[1],ls='--',alpha=0.6,label='Base:30%');axes[0].set_xlabel('IV (%)');axes[0].set_ylabel('Total Theta');axes[0].set_title('Total Theta vs IV');axes[0].legend()
    axes[1].plot(sks,[sum(short_put_theta(sk*Kp,Kp,r_rate,0.30,d/365) for d in range(1,dte+1)) for sk in sks],color=PAL[3],marker='o',markersize=3)
    axes[1].axvline(1.11,color=PAL[1],ls='--',alpha=0.6,label='Base:1.11');axes[1].set_xlabel('S/K');axes[1].set_ylabel('Total Theta');axes[1].set_title('Total Theta vs Moneyness');axes[1].legend()
    fp1=[];fp2=[]
    for s in sigs:t=sum(short_put_theta(100,Kp,r_rate,s,d/365) for d in range(1,dte+1));f=sum(short_put_theta(100,Kp,r_rate,s,d/365) for d in range(1,23));fp1.append(f/t*100 if t>0 else 50)
    for sk in sks:t=sum(short_put_theta(sk*Kp,Kp,r_rate,0.30,d/365) for d in range(1,dte+1));f=sum(short_put_theta(sk*Kp,Kp,r_rate,0.30,d/365) for d in range(1,23));fp2.append(f/t*100 if t>0 else 50)
    axes[2].plot(sigs*100,fp1,color=PAL[0],marker='o',markersize=3,label='Varying IV')
    ax2=axes[2].twiny();ax2.plot(sks,fp2,color=PAL[3],marker='s',markersize=3,label='Varying S/K')
    axes[2].set_xlabel('IV (%)',color=PAL[0]);axes[2].set_ylabel('First-Half Theta (%)');ax2.set_xlabel('S/K',color=PAL[3])
    axes[2].set_title('Front-Loading Sensitivity');axes[2].legend(loc='upper left',fontsize=7);ax2.legend(loc='upper right',fontsize=7)
    fig.suptitle('Sensitivity Analysis: Key Parameter Variations (45 DTE, K=$90)',fontsize=11,fontweight='bold');fig.tight_layout(rect=[0,0,1,0.95]);save(fig,'fig_sensitivity')

def fig_bench_norm():
    np.random.seed(55);dt_=1/252;mb=5000
    cfgs=[('ATM CSP (K=100)',100,1.0,0),('OTM CSP (K=95)',95,1.0,0),('OTM CSP managed',95,0.50,21),('Credit Spread 95/90',None,0.50,21)]
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,5));res=[]
    for ci,(nm,Kp,tgt,fl) in enumerate(cfgs):
        dte=45;pnls=[]
        for _ in range(500):
            S=100
            if Kp is None:
                cts=int(mb/500);prem=(bs_put_price(100,95,r_rate,0.25,dte/365)-bs_put_price(100,90,r_rate,0.25,dte/365))*100*cts;iv0=prem;cl=False
                for d in range(dte):
                    Tr=(dte-d)/365
                    if Tr<=1e-6:break
                    cur=(bs_put_price(S,95,r_rate,0.25,Tr)-bs_put_price(S,90,r_rate,0.25,Tr))*100*cts
                    if tgt<1 and iv0>0 and(iv0-cur)/iv0>=tgt:pnls.append(iv0-cur);cl=True;break
                    if fl>0 and(dte-d)<=fl:pnls.append(iv0-cur);cl=True;break
                    S=S*np.exp((r_rate-0.5*0.18**2)*dt_+0.18*np.sqrt(dt_)*np.random.standard_normal())
                if not cl:pnls.append(prem-(max(95-S,0)-max(90-S,0))*100*cts)
            else:
                cts=max(1,int(mb/(Kp*100)));prem=bs_put_price(100,Kp,r_rate,0.25,dte/365)*100*cts;iv0=prem;cl=False
                for d in range(dte):
                    Tr=(dte-d)/365
                    if Tr<=1e-6:break
                    cur=bs_put_price(S,Kp,r_rate,0.25,Tr)*100*cts
                    if tgt<1 and iv0>0 and(iv0-cur)/iv0>=tgt:pnls.append(iv0-cur);cl=True;break
                    if fl>0 and(dte-d)<=fl:pnls.append(iv0-cur);cl=True;break
                    S=S*np.exp((r_rate-0.5*0.18**2)*dt_+0.18*np.sqrt(dt_)*np.random.standard_normal())
                if not cl:pnls.append(iv0-max(Kp-S,0)*100*cts)
        pnls=np.array(pnls);sr_=np.mean(pnls)/np.std(pnls)*np.sqrt(252/45) if np.std(pnls)>0 else 0
        res.append((nm,sr_,np.mean(pnls>0)*100,np.mean(pnls)/mb*100));a1.plot(np.cumsum(pnls),color=PAL[ci],lw=1.3,label=f'{nm[:20]} SR={sr_:.2f}')
    a1.set_xlabel('Trade #');a1.set_ylabel('Cumulative P&L ($)');a1.set_title('Equal-Margin ($5,000)');a1.legend(fontsize=7);a1.axhline(0,color='#9CA3AF',lw=0.5)
    rois=[r[3] for r in res];best=max(rois)
    a2.barh(range(len(res)),rois,color=[PAL[0] if r>=best*0.8 else '#D1D5DB' for r in rois],edgecolor='white',height=0.55)
    a2.set_yticks(range(len(res)));a2.set_yticklabels([r[0] for r in res],fontsize=8);a2.set_xlabel('ROI per Trade (%)');a2.set_title('Margin-Normalized Return')
    fig.suptitle('Benchmark: Equal Margin Budget ($5,000)',fontsize=10,fontweight='bold',y=1.01);fig.tight_layout();save(fig,'fig_bench_norm')

def fig_matrix():
    from matplotlib.colors import Normalize
    fig,ax=plt.subplots(figsize=(7,5.5));sks=[1.00,1.05,1.10,1.15,1.20,1.30,1.40];ivs=[0.30,0.40,0.60,0.80,1.00,1.20,1.50]
    grid=np.array([[theta_peak_dte(sk*K,K,iv) for sk in sks] for iv in ivs])
    cmap=cm.RdYlGn_r
    norm=Normalize(vmin=grid.min(), vmax=grid.max())
    im=ax.imshow(grid,cmap=cmap,norm=norm,aspect='equal',extent=[-0.5,len(sks)-0.5,-0.5,len(ivs)-0.5],origin='lower')
    for i in range(len(ivs)):
        for j in range(len(sks)):
            val=grid[i,j]
            r,g,b,_=cmap(norm(val))
            lum=0.299*r+0.587*g+0.114*b
            txt_color='white' if lum<0.55 else '#1F2937'
            ax.text(j,i,f'{val:.0f}',ha='center',va='center',fontsize=9,fontweight='bold',color=txt_color)
    ax.set_xticks(range(len(sks)));ax.set_xticklabels([f'{s:.2f}' for s in sks]);ax.set_yticks(range(len(ivs)));ax.set_yticklabels([f'{int(v*100)}%' for v in ivs])
    ax.set_xlabel('Moneyness (S/K)');ax.set_ylabel('Implied Volatility');ax.set_title('Peak Theta DTE by Moneyness \u00d7 IV\nGreen = peaks near expiry \u00b7 Red = peaks early')
    plt.colorbar(im,label='DTE at Peak',shrink=0.8);save(fig,'fig_matrix')

def fig_cases():
    np.random.seed(42);S0=100;Kp=95;dte=45;n=500;dt_=1/252;margin=Kp*100
    cases=[('2017 Low-Vol Grind',0.12,0.10,0.03,0,0,0),('Feb 2018 Volmageddon',0.15,0.35,-0.05,5.0,-0.03,0.25),('Mar 2020 Crash',0.20,0.60,-0.15,8.0,-0.08,0.30),('2022 Bear Grind',0.28,0.25,-0.04,0.5,-0.02,0.10)]
    fig,axes=plt.subplots(2,2,figsize=(10,7.5))
    for idx,(nm,iv,rv,dr,lam,mj,sj) in enumerate(cases):
        ax=axes[idx//2][idx%2];ph=[];pm=[]
        for _ in range(n):
            S=S0;prem=bs_put_price(S0,Kp,r_rate,iv,dte/365)*100;iv0=prem;clm=False;pnl_m=0
            for d in range(dte):
                Tr=(dte-d)/365
                if Tr<=1e-6:break
                if not clm:
                    cur=bs_put_price(S,Kp,r_rate,iv,Tr)*100;pct=(iv0-cur)/iv0 if iv0>0 else 0
                    if pct>=0.50:pnl_m=iv0-cur;clm=True
                    elif(dte-d)<=21:pnl_m=iv0-cur;clm=True
                z=np.random.standard_normal();dS=S*((r_rate+dr)*dt_+rv*np.sqrt(dt_)*z)
                if lam>0:
                    for _ in range(np.random.poisson(lam*dt_)):dS+=S*(np.exp(mj+sj*np.random.standard_normal())-1)
                S=max(S+dS,0.01)
            fv=max(Kp-S,0)*100;ph.append((prem-fv)/margin*100)
            if not clm:pnl_m=prem-fv
            pm.append(pnl_m/margin*100)
        h=np.sort(ph);m=np.sort(pm);cdf=np.arange(1,n+1)/n
        ax.plot(h,cdf,color='#1E40AF',ls='-',lw=2.2,label='Hold');ax.plot(m,cdf,color='#7C3AED',ls='--',lw=2.2,label='Managed')
        for arr,color in [(np.array(ph),'#1E40AF'),(np.array(pm),'#7C3AED')]:
            med=np.median(arr);p5=np.percentile(arr,5)
            ax.plot(med,0.50,'o',color=color,markersize=6,zorder=5);ax.plot(p5,0.05,'s',color=color,markersize=6,zorder=5)
            ax.annotate(f'{med:.1f}%',(med,0.50),textcoords='offset points',xytext=(0,8),fontsize=7,color=color,ha='center')
            ax.annotate(f'{p5:.1f}%',(p5,0.05),textcoords='offset points',xytext=(0,-10),fontsize=7,color=color,ha='center')
        ax.axhline(0.25,color='#9CA3AF',lw=0.7,ls=':');ax.axvline(0,color='#D1D5DB',lw=0.5)
        ax.set_title(nm,fontsize=10);ax.set_xlabel('P&L (% margin)');ax.set_ylabel('Cumulative Prob');ax.set_ylim(0,1);ax.legend(fontsize=7)
    fig.suptitle('CDF by Simulated Regime\n\u25cf=Median \u25a0=5th %ile',fontsize=10,fontweight='bold');fig.tight_layout(rect=[0,0,1,0.94]);save(fig,'fig_cases')

def fig_lifecycle():
    np.random.seed(11);S0=100;Klc=95;iv=0.28;rv=0.22;dte=45;dt_=1/252
    prem=bs_put_price(S0,Klc,r_rate,iv,dte/365)*100;margin=Klc*100
    spots=[S0];ov=[prem];po=[0];td=[short_put_theta(S0,Klc,r_rate,iv,dte/365)*100];S=S0
    for d in range(1,dte):
        S=S*np.exp((r_rate-0.5*rv**2)*dt_+rv*np.sqrt(dt_)*np.random.standard_normal());spots.append(S)
        Tr=(dte-d)/365;v=bs_put_price(S,Klc,r_rate,iv,Tr)*100 if Tr>0 else max(Klc-S,0)*100
        ov.append(v);po.append(prem-v);td.append(short_put_theta(S,Klc,r_rate,iv,Tr)*100 if Tr>0 else 0)
    pp=[p/prem*100 for p in po];h50=next((d for d,pct in enumerate(pp) if pct>=50),None)
    fd=dte-21;ed=h50 if h50 and h50<fd else fd
    fig,(a1,a2,a3)=plt.subplots(3,1,figsize=(9,10),sharex=True);days=list(range(len(spots)))
    a1.plot(days,spots,color=PAL[0],lw=2);a1.axhline(Klc,color=PAL[1],ls='--',lw=1,label=f'Strike=${Klc}');a1.axvline(ed,color=PAL[3],ls=':',lw=1.5,label=f'Exit Day {ed}')
    mpd=np.argmin(po)
    if mpd<ed:a1.annotate(f'Worst\nS=${spots[mpd]:.1f}',(mpd,spots[mpd]),xytext=(mpd+3,spots[mpd]-2),fontsize=8,color=PAL[1],arrowprops=dict(arrowstyle='->',color=PAL[1]))
    a1.annotate(f'Entry\nS=${S0}',(0,S0),xytext=(3,S0+1.5),fontsize=8,color=PAL[4],arrowprops=dict(arrowstyle='->',color=PAL[4]))
    a1.set_ylabel('Spot ($)');a1.set_title('Panel 1: Price Path');a1.legend(fontsize=7,loc='lower right')
    a2.plot(days,po,color=PAL[0],lw=2,label='Open P&L');a2.axhline(prem*0.50,color=PAL[3],ls='--',lw=1,label='50% target')
    a2.axhline(0,color='#9CA3AF',lw=0.5);a2.axvline(ed,color=PAL[3],ls=':',lw=1.5);a2.axvline(fd,color=PAL[2],ls=':',lw=1,alpha=0.7,label=f'21 DTE floor')
    ep=po[ed];a2.annotate(f'EXIT: 21 DTE\nPnL=${ep:.0f}',(ed,ep),xytext=(ed-12,ep+prem*0.3),fontsize=8,color=PAL[3],fontweight='bold',arrowprops=dict(arrowstyle='->',color=PAL[3],lw=1.5),bbox=dict(boxstyle='round',fc='white',ec=PAL[3],alpha=0.9))
    a2.set_ylabel('Open P&L ($)');a2.set_title('Panel 2: P&L with Triggers');a2.legend(fontsize=7,loc='upper left')
    a3.bar(days[:ed+1],td[:ed+1],color=PAL[0],alpha=0.6,width=0.8);a3.bar(days[ed+1:],td[ed+1:],color='#D1D5DB',alpha=0.3,width=0.8)
    ts=theta_peak_dte(S0,Klc,iv);tsd=dte-ts
    if 0<tsd<dte:a3.axvline(tsd,color=PAL[4],ls='--',lw=1.5,label=f'T* peak (Day {tsd:.0f})')
    a3.axvline(ed,color=PAL[3],ls=':',lw=1.5,label='Exit');a3.set_xlabel('Trading Day');a3.set_ylabel('Daily Theta ($/ct)')
    a3.set_title('Panel 3: Theta Collected (Gray=Forgone)');a3.legend(fontsize=7)
    fig.suptitle('Trade Lifecycle: OTM Short Put (S=$100, K=$95, IV=28%, 45 DTE)',fontsize=12,fontweight='bold',y=1.01);fig.tight_layout();save(fig,'fig_lifecycle')

def fig_path_dep():
    S0=100;Kpd=95;iv=0.25;dte=30;prem=bs_put_price(S0,Kpd,r_rate,iv,dte/365)*100
    np.random.seed(42);pa=[S0];S=S0
    for d in range(dte):t=S0-3*np.sin(np.pi*d/dte);S=S+(t-S)*0.3+0.2*np.random.standard_normal();pa.append(S)
    np.random.seed(7);pb=[S0];S=S0
    for d in range(dte):t=S0-3*np.sin(np.pi*d/dte);S=S+(t-S)*0.15+2.5*np.random.standard_normal();S=max(S,85);pb.append(S)
    pb[-1]=pa[-1]
    def cpnl(path):
        dy=[];cm=[];prev=prem;tot=0
        for d in range(1,len(path)):
            Tr=(dte-d)/365;cur=bs_put_price(path[d],Kpd,r_rate,iv,Tr)*100 if Tr>0 else max(Kpd-path[d],0)*100
            dd=-(cur-prev);dy.append(dd);tot+=dd;cm.append(tot);prev=cur
        return dy,cm
    da,ca=cpnl(pa);db,cb=cpnl(pb)
    rva=np.std(np.diff(np.log(pa)))*np.sqrt(252)*100;rvb=np.std(np.diff(np.log(pb)))*np.sqrt(252)*100
    fig,(a1,a2,a3)=plt.subplots(1,3,figsize=(12,4))
    a1.plot(range(len(pa)),pa,color=PAL[0],lw=2,label='Path A: Smooth');a1.plot(range(len(pb)),pb,color=PAL[1],lw=1.5,label='Path B: Volatile',alpha=0.8)
    a1.axhline(Kpd,color='#9CA3AF',ls='--',lw=1,label=f'K=${Kpd}');a1.set_xlabel('Day');a1.set_ylabel('Spot ($)');a1.set_title('Same Endpoint');a1.legend(fontsize=7)
    a2.bar(range(len(da)),da,alpha=0.6,color=PAL[0],label='A',width=0.8);a2.bar(range(len(db)),db,alpha=0.4,color=PAL[1],label='B',width=0.5)
    a2.set_xlabel('Day');a2.set_ylabel('Daily P&L ($)');a2.set_title('Daily P&L');a2.axhline(0,color='#9CA3AF',lw=0.5);a2.legend(fontsize=7)
    a3.plot(range(len(ca)),ca,color=PAL[0],lw=2,label=f'A: ${ca[-1]:.0f}');a3.plot(range(len(cb)),cb,color=PAL[1],lw=2,label=f'B: ${cb[-1]:.0f}')
    a3.set_xlabel('Day');a3.set_ylabel('Cumulative P&L ($)');a3.set_title('Cumulative');a3.axhline(0,color='#9CA3AF',lw=0.5);a3.legend(fontsize=7)
    fig.suptitle(f'Path Dependency: Short Put (K=${Kpd}, IV=25%, 30 DTE)\nA RV:{rva:.0f}% | B RV:{rvb:.0f}% | Same terminal',fontsize=10,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,0.92]);save(fig,'fig_path_dep')

def fig_v5_greeks():
    """Second-order Greek profiles vs DTE for a representative short OTM put."""
    dtes = np.arange(2, 91)
    S, sig = 1.15 * K, 0.80
    vom, van, chm, spd = [], [], [], []
    for d in dtes:
        T = d / 365.0
        vom.append(bs_vomma(S, K, r_rate, sig, T))
        van.append(bs_vanna(S, K, r_rate, sig, T))
        chm.append(bs_charm_put(S, K, r_rate, sig, T) / 365.0)
        spd.append(bs_speed(S, K, r_rate, sig, T))
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    panels = [
        (axes[0, 0], vom, 'Vomma (d²V/dσ²)', 'Vol convexity'),
        (axes[0, 1], van, 'Vanna (d²V/dS dσ)', 'Delta–vol cross'),
        (axes[1, 0], chm, 'Charm (dΔ/dt, per day)', 'Delta decay'),
        (axes[1, 1], spd, 'Speed (dΓ/dS)', 'Gamma convexity'),
    ]
    for ax, vals, ylab, subtitle in panels:
        ax.plot(dtes[::-1], vals, color=PAL[0], lw=2.2)
        ax.set_xlabel('Days to Expiry')
        ax.set_ylabel(ylab)
        ax.set_title(subtitle)
        ax.set_xlim(90, 0)
        ax.axhline(0, color='#9CA3AF', lw=0.5)
    fig.suptitle(
        'Second-Order Greeks: Short OTM Put (S/K=1.15, K=$100, σ=80%)',
        fontsize=11, fontweight='bold', y=1.01,
    )
    fig.tight_layout()
    save(fig, 'fig_v5_greeks')

def fig_var_premium():
    """Gamma P&L from realized vs implied variance over a 30-day hold."""
    np.random.seed(11)
    S0, sig_iv, dte = 100.0, 0.25, 30
    n_paths, dt_ = 800, 1 / 252
    rv_levels = [0.12, 0.18, 0.25, 0.35, 0.50]
    gamma_pnl = []
    for rv in rv_levels:
        totals = []
        for _ in range(n_paths):
            S, cum = S0, 0.0
            for d in range(dte):
                Tr = (dte - d) / 365.0
                if Tr <= 1e-8:
                    break
                g = bs_gamma(S, K, r_rate, sig_iv, Tr)
                z = np.random.standard_normal()
                dS = S * (rv * np.sqrt(dt_) * z)
                cum += 0.5 * g * dS * dS
                S = max(S + dS, 0.01)
            totals.append(cum * 100)
        gamma_pnl.append(np.median(totals))
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [PAL[3] if rv < sig_iv else PAL[1] for rv in rv_levels]
    bars = ax.bar([f'{int(rv * 100)}%' for rv in rv_levels], gamma_pnl, color=colors, edgecolor='white', lw=0.8)
    ax.axhline(0, color='#9CA3AF', lw=0.8)
    ax.axvline(2.5, color=PAL[0], ls='--', lw=1.2, alpha=0.8)
    ax.text(2.45, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] else 1, f'IV={int(sig_iv * 100)}%', fontsize=8, color=PAL[0], ha='right')
    for bar, val in zip(bars, gamma_pnl):
        ax.text(bar.get_x() + bar.get_width() / 2, val, f'${val:.0f}', ha='center', va='bottom' if val >= 0 else 'top', fontsize=8)
    ax.set_xlabel('Realized Volatility (30-day hold)')
    ax.set_ylabel('Median Gamma P&L ($/contract)')
    ax.set_title('Realized vs Implied Variance: Gamma P&L\nShort ATM Put, σ_implied = 25%')
    save(fig, 'fig_var_premium')

def fig_greek_evolution():
    """First-order Greeks vs DTE at multiple spot levels (static IV)."""
    dtes = np.arange(1, 91)
    sig = 0.80
    spot_levels = [(1.10, 'S/K=1.10 (entry)'), (1.00, 'S/K=1.00'), (0.95, 'S/K=0.95 (decline)')]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    greek_fns = [
        (axes[0, 0], lambda S, T: -bs_delta_put(S, K, r_rate, sig, T), 'Position Δ (short put)'),
        (axes[0, 1], lambda S, T: -bs_gamma(S, K, r_rate, sig, T), 'Position Γ (short put)'),
        (axes[1, 0], lambda S, T: short_put_theta(S, K, r_rate, sig, T), 'Daily θ collected ($/sh)'),
        (axes[1, 1], lambda S, T: -bs_vega(S, K, r_rate, sig, T) / 100, 'Position Vega ($/1% IV)'),
    ]
    for ax, fn, ylab in greek_fns:
        for i, (sk, label) in enumerate(spot_levels):
            S = sk * K
            vals = [fn(S, d / 365.0) for d in dtes]
            ax.plot(dtes[::-1], vals, color=PAL[i], lw=2, label=label)
        ax.set_xlabel('Days to Expiry')
        ax.set_ylabel(ylab)
        ax.set_xlim(90, 0)
        ax.axhline(0, color='#9CA3AF', lw=0.5)
        ax.legend(fontsize=7, loc='best')
    fig.suptitle(
        'Dynamic Greek Evolution: OTM Short Put (K=$100, σ=80%)\nSpot shift re-times gamma/theta peaks',
        fontsize=11, fontweight='bold', y=1.01,
    )
    fig.tight_layout()
    save(fig, 'fig_greek_evolution')

def fig_hedging():
    """Unhedged vs daily delta-hedged short put on a volatile path."""
    from math import exp, sqrt
    np.random.seed(42)
    S0, Kp, iv, dte = 110.0, 100.0, 0.25, 45
    dt_, rv = 1 / 252, 0.38
    prem = bs_put_price(S0, Kp, r_rate, iv, dte / 365) * 100
    spots = [S0]
    for _ in range(dte):
        z = np.random.standard_normal()
        S = spots[-1] * exp((r_rate - 0.5 * rv ** 2) * dt_ + rv * sqrt(dt_) * z)
        spots.append(max(S, 50.0))
    unhedged, hedged = [], []
    stock_pos = 0.0
    hedge_cum = 0.0
    for d in range(dte + 1):
        S = spots[d]
        Tr = (dte - d) / 365.0
        opt_val = max(Kp - S, 0) * 100 if Tr <= 1e-8 else bs_put_price(S, Kp, r_rate, iv, Tr) * 100
        if d > 0:
            hedge_cum += stock_pos * (spots[d] - spots[d - 1])
        unhedged.append(prem - opt_val)
        hedged.append(prem - opt_val + hedge_cum)
        stock_pos = bs_delta_put(S, Kp, r_rate, iv, Tr) * 100 if Tr > 1e-8 else 0.0
    days = list(range(dte + 1))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    a1.plot(days, spots, color=PAL[0], lw=2)
    a1.axhline(Kp, color=PAL[1], ls='--', lw=1, label=f'Strike ${Kp:.0f}')
    a1.set_ylabel('Spot ($)')
    a1.set_title('Panel 1: Volatile Path (RV ≈ 38%)')
    a1.legend(fontsize=8)
    a2.plot(days, unhedged, color=PAL[1], lw=2.2, label='Unhedged short put')
    a2.plot(days, hedged, color=PAL[3], lw=2.2, ls='--', label='Delta-hedged (daily rebalance)')
    a2.axhline(0, color='#9CA3AF', lw=0.5)
    a2.set_xlabel('Trading Day')
    a2.set_ylabel('Cumulative P&L ($/contract)')
    a2.set_title('Panel 2: Hedging Isolates Theta from Direction')
    a2.legend(fontsize=8)
    fig.suptitle(
        'Hedging Framework: Short OTM Put (S=$110, K=$100, IV=25%, 45 DTE)',
        fontsize=11, fontweight='bold', y=1.01,
    )
    fig.tight_layout()
    save(fig, 'fig_hedging')

def _skew_iv(S, K, atm_iv=0.22, skew=0.55):
    """Simple equity skew: higher IV for lower strikes."""
    from math import log
    lm = log(K / S)
    return max(atm_iv + skew * max(-lm, 0) ** 0.85 + 0.04 * max(lm, 0), 0.08)

def fig_surface_sticky():
    """MTM impact on short put under sticky strike vs sticky delta after spot drop."""
    S0, S1, Kp, T = 110.0, 100.0, 95.0, 30 / 365
    iv_ss = _skew_iv(S0, Kp)
    iv_sd = _skew_iv(S1, Kp)
    iv_flat = 0.25
    prem0 = bs_put_price(S0, Kp, r_rate, iv_ss, T) * 100
    scenarios = ['Sticky Strike\n(IV fixed at K)', 'Sticky Delta\n(surface moves)', 'Flat BS\n(IV = 25%)']
    ivs = [iv_ss, iv_sd, iv_flat]
    mtm = [bs_put_price(S1, Kp, r_rate, iv, T - 1 / 365) * 100 for iv in ivs]
    pnl = [prem0 - m for m in mtm]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.8))
    sk = np.linspace(0.75, 1.15, 60)
    a1.plot(sk, [_skew_iv(S0, s * Kp) * 100 for s in sk], color=PAL[0], lw=2, label='Surface at S=$110')
    a1.plot(sk, [_skew_iv(S1, s * Kp) * 100 for s in sk], color=PAL[1], lw=2, ls='--', label='Surface at S=$100')
    a1.axvline(Kp / S0, color='#9CA3AF', ls=':', lw=1)
    a1.axvline(Kp / S1, color='#9CA3AF', ls=':', lw=1)
    a1.set_xlabel('Moneyness (K/S)')
    a1.set_ylabel('Implied Vol (%)')
    a1.set_title('Skew Surface Shift (Sticky Delta)')
    a1.legend(fontsize=7)
    colors = [PAL[3], PAL[1], PAL[4]]
    bars = a2.bar(scenarios, pnl, color=colors, edgecolor='white', lw=0.8)
    a2.axhline(0, color='#9CA3AF', lw=0.5)
    a2.set_ylabel('Short Put P&L ($/contract)')
    a2.set_title('Spot Drop $110 → $100 (1 day elapsed)')
    for bar, val, iv in zip(bars, pnl, ivs):
        a2.text(bar.get_x() + bar.get_width() / 2, val, f'${val:.0f}\nIV={iv*100:.0f}%',
                ha='center', va='bottom' if val >= 0 else 'top', fontsize=8)
    fig.suptitle('Volatility Surface Dynamics: Sticky Strike vs Sticky Delta\nShort 95P entered at S=$110, 30 DTE',
                 fontsize=10, fontweight='bold', y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save(fig, 'fig_surface_sticky')

def fig_model_risk():
    """BS vs Merton vs stoch-vol-inspired effective IV on OTM short put theta."""
    from math import log
    dtes = np.arange(2, 91)
    S, Kp = 1.15 * K, K
    bs_t, me_t, sv_t = [], [], []
    for d in dtes:
        T = d / 365.0
        bs_t.append(short_put_theta(S, Kp, r_rate, 0.25, T))
        me_t.append(short_put_theta_merton(S, Kp, r_rate, 0.20, T, 2.0, -0.04, 0.18))
        iv_eff = 0.25 + 0.12 * max(0, log(Kp / S)) + 0.08 * 0.25
        sv_t.append(short_put_theta(S, Kp, r_rate, iv_eff, T))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.8))
    a1.plot(dtes[::-1], bs_t, color=PAL[0], lw=2, label='Black-Scholes (flat σ=25%)')
    a1.plot(dtes[::-1], me_t, color=PAL[1], lw=2, ls='--', label='Merton (jumps)')
    a1.plot(dtes[::-1], sv_t, color=PAL[3], lw=2, ls='-.', label='Stoch-vol adjusted (skew+ρ)')
    a1.set_xlabel('Days to Expiry')
    a1.set_ylabel('Daily θ ($/share)')
    a1.set_title('Model Comparison: Theta Profile')
    a1.set_xlim(90, 0)
    a1.legend(fontsize=7)
    models = ['BS', 'Merton', 'Stoch-Vol\n(adj.)']
    peaks = [max(bs_t), max(me_t), max(sv_t)]
    tstars = [dtes[::-1][np.argmax(bs_t)], dtes[::-1][np.argmax(me_t)], dtes[::-1][np.argmax(sv_t)]]
    a2.bar(models, peaks, color=[PAL[0], PAL[1], PAL[3]], edgecolor='white')
    a2.set_ylabel('Peak Daily θ ($/share)')
    a2.set_title('Peak Theta by Model')
    for i, (p, t) in enumerate(zip(peaks, tstars)):
        a2.text(i, p, f'T*≈{t}d', ha='center', va='bottom', fontsize=8)
    fig.suptitle('Model Risk: OTM Short Put (S/K=1.15, K=$100)', fontsize=11, fontweight='bold', y=1.02)
    fig.tight_layout()
    save(fig, 'fig_model_risk')

def fig_execution():
    """Effective spreads by moneyness and stress widening."""
    mlabels = ['ATM\n1.00', '1.05', '1.10', '1.20', '1.30']
    half_sp = [2.0, 2.2, 2.8, 4.5, 7.0]
    vix = ['12', '18', '25', '35', '45']
    mult = [1.0, 1.15, 1.55, 2.6, 4.2]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.8))
    bars = a1.bar(mlabels, half_sp, color=PAL[0], alpha=0.85, edgecolor='white')
    a1.set_ylabel('Effective Half-Spread (%)')
    a1.set_xlabel('Moneyness (S/K)')
    a1.set_title('Spread by Moneyness (Muravyev & Pearson 2020)')
    for bar, val in zip(bars, half_sp):
        a1.text(bar.get_x() + bar.get_width() / 2, val, f'{val:.1f}%', ha='center', va='bottom', fontsize=8)
    a2.plot(vix, mult, 'o-', color=PAL[1], lw=2.2, markersize=7)
    a2.axhline(1.0, color='#9CA3AF', ls='--', lw=0.8)
    a2.set_xlabel('VIX Level')
    a2.set_ylabel('Spread Multiplier vs Normal')
    a2.set_title('Stress Widening (Cao et al. 2024 pattern)')
    fig.suptitle('Execution Microstructure: Cost and Liquidity', fontsize=11, fontweight='bold', y=1.02)
    fig.tight_layout()
    save(fig, 'fig_execution')

def fig_v6_pilot():
    """Real SPY chain pilot backtest (optional — skips if trades file missing)."""
    import pandas as pd
    path = os.path.join(REPO_ROOT, 'data', 'derived', 'trades_backtest.parquet')
    if not os.path.isfile(path):
        print('  skip fig_v6_pilot (no trades_backtest.parquet)')
        return
    trades = pd.read_parquet(path)
    trades['entry_date'] = pd.to_datetime(trades['entry_date'])
    order = ['crisis', 'elevated', 'normal', 'low']
    regimes = [r for r in order if r in set(trades['regime'])]
    x = np.arange(len(regimes))
    w = 0.35
    hold_med, mgd_med = [], []
    for r in regimes:
        g = trades[trades['regime'] == r]
        hold_med.append(g[g['strategy'] == 'hold']['pnl_net'].median())
        mgd_med.append(g[g['strategy'] == 'managed']['pnl_net'].median())
    n_entries = trades['entry_date'].nunique()
    d0 = trades['entry_date'].min().strftime('%Y-%m-%d')
    d1 = trades['entry_date'].max().strftime('%Y-%m-%d')
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w / 2, hold_med, w, label='Hold', color='#1E40AF')
    ax.bar(x + w / 2, mgd_med, w, label='Managed', color='#7C3AED')
    ax.axhline(0, color='#D1D5DB', lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([r.title() for r in regimes])
    ax.set_ylabel('Median Net P&L ($/contract)')
    ax.set_title(
        f'Pilot SPY Chain Backtest by VIX Regime\n'
        f'{n_entries} entry weeks ({d0} to {d1}); v6.4 exit-reason methodology'
    )
    ax.legend()
    for i, (h, m) in enumerate(zip(hold_med, mgd_med)):
        ax.text(i - w / 2, h, f'${h:.0f}', ha='center', va='bottom', fontsize=8)
        ax.text(i + w / 2, m, f'${m:.0f}', ha='center', va='bottom', fontsize=8)
        if abs(h - m) < 0.5:
            ax.text(i, max(h, m) + 8, 'tie', ha='center', va='bottom', fontsize=7, color='#6B7280')
    save(fig, 'fig_v6_pilot')

if __name__=='__main__':
    print("Generating all charts...")
    fig01();fig02();fig03();fig04();fig05();fig06();fig07();fig08();fig09();fig10();fig11()
    fig_sens_grid();fig_skew();fig_merton();fig_costs();fig_risk();fig_regime()
    fig_risk_multi();fig_sweep();fig_dte_ci();fig_sensitivity();fig_bench_norm()
    fig_matrix();fig_cases();fig_lifecycle();fig_path_dep()
    fig_v5_greeks();fig_var_premium()
    fig_greek_evolution();fig_hedging()
    fig_surface_sticky();fig_model_risk();fig_execution()
    fig_v6_pilot()
    print(f"Done. {len(os.listdir(OUTDIR))} charts in {OUTDIR}")
