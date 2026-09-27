#!/usr/bin/env python3
"""Neutral classification of public geopolitical events into market transmission channels."""


def classify_geopolitical_event(event):
    text=str(event.get('text','')).lower()
    themes=[]; channels=[]
    def add(seq, value):
        if value not in seq: seq.append(value)

    if 'iran' in text: add(themes,'iran')
    if 'hormuz' in text or 'strait' in text and ('tanker' in text or 'shipping' in text):
        add(themes,'shipping_chokepoint'); add(channels,'shipping'); add(channels,'energy_supply')
    if any(k in text for k in ['sanction','ofac','treasury designat']):
        add(themes,'sanctions'); add(channels,'fx'); add(channels,'rates')
        if any(k in text for k in ['oil','energy','shipping','iran']): add(channels,'energy_supply')
        if any(k in text for k in ['digital asset','crypto','bitcoin','stablecoin','exchange']): add(channels,'crypto')
    if any(k in text for k in ['war','attack','strike','missile','military','conflict','blockade','retaliat']):
        add(themes,'armed_conflict'); add(channels,'risk_aversion'); add(channels,'volatility')
    if any(k in text for k in ['oil','crude','lng','tanker','pipeline','refiner']): add(channels,'energy_supply')
    if any(k in text for k in ['talks','negotiat','ceasefire','deal','diplom']): add(themes,'diplomacy')
    return {'themes':themes,'channels':channels,'actor':event.get('actor'),'text':event.get('text','')}


def transmission_map(classified):
    channels=set(classified.get('channels',[])); themes=set(classified.get('themes',[]))
    assets=[]
    def add(*vals):
        for v in vals:
            if v not in assets: assets.append(v)
    if 'energy_supply' in channels or 'shipping_chokepoint' in themes:
        add('WTI','BRENT','NATGAS','XLE')
    if {'risk_aversion','volatility'} & channels or {'iran','armed_conflict','shipping_chokepoint'} & themes:
        add('GOLD','DXY','VIX','VXN','TNX','NQ','ES','YM','RTY','BTC')
    if 'fx' in channels: add('DXY')
    if 'rates' in channels: add('TNX')
    if 'crypto' in channels: add('BTC','ETH')
    return {
        'assets':assets,
        'channels':list(classified.get('channels',[])),
        'themes':list(classified.get('themes',[])),
        'policy':'measure observed reactions; do not infer political intent or unqualified causation',
    }
