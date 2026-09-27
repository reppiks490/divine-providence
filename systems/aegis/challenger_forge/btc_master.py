from __future__ import annotations
from .core import BaseComponentAdapter, ComponentResult

def _ema(values,length):
    out=[None]*len(values)
    if not values: return out
    a=2.0/(length+1.0); e=values[0]; out[0]=e
    for i in range(1,len(values)):
        e=a*values[i]+(1-a)*e; out[i]=e
    return out

class ADXTrendStrengthAdapter(BaseComponentAdapter):
    component_id='BTCM-STRENGTH-ADX-001'; component_version='0.8.0'; role='feature'
    def __init__(self,length=14,threshold=20.0): self.length=int(length); self.threshold=float(threshold)
    def run(self,ctx):
        self.validate_context(ctx); h,l,c=ctx.series['high'],ctx.series['low'],ctx.series['close']; n=len(c)
        tr=[0.0]*n; pdm=[0.0]*n; mdm=[0.0]*n
        for i in range(1,n):
            up=h[i]-h[i-1]; dn=l[i-1]-l[i]
            pdm[i]=up if up>dn and up>0 else 0.0; mdm[i]=dn if dn>up and dn>0 else 0.0
            tr[i]=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
        out=[None]*n
        for i in range(2*self.length,n):
            atr=sum(tr[i-self.length+1:i+1])/self.length
            p=100*(sum(pdm[i-self.length+1:i+1])/self.length)/atr if atr else 0.0
            m=100*(sum(mdm[i-self.length+1:i+1])/self.length)/atr if atr else 0.0
            dx=100*abs(p-m)/(p+m) if p+m else 0.0
            out[i]={'adx_proxy':dx,'gate_open':dx>=self.threshold,'event_time_index':i}
        return ComponentResult(self.component_id,self.component_version,list(ctx.timestamps),out,
                               {'corpus_ids':list(ctx.corpus_ids),'length':self.length,'threshold':self.threshold},
                               available_at=list(ctx.timestamps))

class IchimokuRegimeAdapter(BaseComponentAdapter):
    component_id='BTCM-REGIME-ICHI-001'; component_version='0.8.0'; role='regime'
    def __init__(self,tenkan=9,kijun=26,senkou_b=52): self.tenkan=int(tenkan); self.kijun=int(kijun); self.senkou_b=int(senkou_b)
    def run(self,ctx):
        self.validate_context(ctx); h,l,c=ctx.series['high'],ctx.series['low'],ctx.series['close']; out=[None]*len(c)
        for i in range(self.senkou_b-1,len(c)):
            t=(max(h[i-self.tenkan+1:i+1])+min(l[i-self.tenkan+1:i+1]))/2
            k=(max(h[i-self.kijun+1:i+1])+min(l[i-self.kijun+1:i+1]))/2
            a=(t+k)/2; b=(max(h[i-self.senkou_b+1:i+1])+min(l[i-self.senkou_b+1:i+1]))/2
            top=max(a,b); bot=min(a,b)
            state='BULL' if c[i]>top and t>k else ('BEAR' if c[i]<bot and t<k else 'NEUTRAL')
            out[i]={'trend_state':state,'tenkan':t,'kijun':k,'cloud_top_now':top,'cloud_bottom_now':bot,
                    'event_time_index':i,'note':'causal non-displaced decision representation'}
        return ComponentResult(self.component_id,self.component_version,list(ctx.timestamps),out,
                               {'corpus_ids':list(ctx.corpus_ids),'tenkan':self.tenkan,'kijun':self.kijun,'senkou_b':self.senkou_b},
                               available_at=list(ctx.timestamps))

class TrendPullbackAdapter(BaseComponentAdapter):
    component_id='BTCM-ENTRY-PULLBACK-001'; component_version='0.8.0'; role='alpha'
    def __init__(self,fast=9,slow=21,proximity=0.004): self.fast=int(fast); self.slow=int(slow); self.proximity=float(proximity)
    def run(self,ctx):
        self.validate_context(ctx); c=ctx.series['close']; f=_ema(c,self.fast); s=_ema(c,self.slow); out=[None]*len(c)
        for i in range(self.slow,len(c)):
            trend=1 if f[i]>s[i] else -1; dist=abs(c[i]-f[i])/c[i] if c[i] else 1.0
            out[i]={'direction':trend if dist<=self.proximity else 0,'ema_fast':f[i],'ema_slow':s[i],
                    'proximity':dist,'event_time_index':i}
        return ComponentResult(self.component_id,self.component_version,list(ctx.timestamps),out,
                               {'corpus_ids':list(ctx.corpus_ids),'fast':self.fast,'slow':self.slow,'proximity':self.proximity},
                               available_at=list(ctx.timestamps))

class CompositeExitAdapter(BaseComponentAdapter):
    component_id='BTCM-EXIT-COMPOSITE-001'; component_version='0.8.0'; role='exit'
    def __init__(self,confirmation_count=2): self.confirmation_count=int(confirmation_count)
    def run(self,ctx):
        self.validate_context(ctx); keys=['tk_cross','cloud_breach','rsi_deceleration','ema_cross','kijun_break']
        for k in keys:
            if k not in ctx.series: raise ValueError(f'missing {k}')
        out=[None]*len(ctx.timestamps)
        for i in range(len(ctx.timestamps)):
            votes=sum(1 for k in keys if bool(ctx.series[k][i]))
            out[i]={'exit_score':votes,'exit_now':votes>=self.confirmation_count,'event_time_index':i}
        return ComponentResult(self.component_id,self.component_version,list(ctx.timestamps),out,
                               {'corpus_ids':list(ctx.corpus_ids),'confirmation_count':self.confirmation_count},
                               available_at=list(ctx.timestamps))
