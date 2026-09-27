#!/usr/bin/env python3
import re
IMPACT={'low':1,'medium':2,'med':2,'high':3,'non-economic':0,'holiday':0}


def _num(v):
    if v is None: return None
    s=str(v).strip().replace(',','')
    pct=s.endswith('%')
    if pct: s=s[:-1]
    mult=1.0
    if s and s[-1:].upper() in {'K','M','B','T'}:
        mult={'K':1e3,'M':1e6,'B':1e9,'T':1e12}[s[-1].upper()]; s=s[:-1]
    m=re.search(r'-?\d+(?:\.\d+)?',s)
    return float(m.group())*mult if m else None


def surprise_score(actual, forecast):
    a,f=_num(actual),_num(forecast)
    if a is None or f is None:
        return {'difference':None,'direction':'unknown'}
    d=a-f
    return {'difference':d,'direction':'above_forecast' if d>0 else ('below_forecast' if d<0 else 'in_line')}


def normalize_event(row, timezone='UTC'):
    impact=str(row.get('impact','')).strip().lower()
    return {
        'event_family':'macro_calendar','title':row.get('title') or row.get('event'),
        'currency':row.get('currency') or row.get('country'),'date':row.get('date'),'time':row.get('time'),'timezone':timezone,
        'impact':impact,'impact_rank':IMPACT.get(impact,0),'actual':row.get('actual'),'forecast':row.get('forecast'),
        'previous':row.get('previous'),'revised_previous':row.get('revised_previous'),'surprise':surprise_score(row.get('actual'),row.get('forecast')),
        'source_class':'forex_factory_calendar'
    }
