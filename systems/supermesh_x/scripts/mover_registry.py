#!/usr/bin/env python3
"""Configurable registry for public figures and roles that can move markets."""


def default_registry():
    return {
        'entities': {
            'donald_trump': {
                'id':'donald_trump','name':'Donald Trump',
                'public_channels':['public_social','official_statements','speeches','press'],
                'asset_exposure':['NQ','ES','YM','RTY','VIX','VXN','DXY','TNX','BTC','OIL','GOLD','SEMIS'],
                'topics':['trade','tariffs','fiscal','regulation','geopolitics','technology','energy','crypto'],
            },
            'elon_musk': {
                'id':'elon_musk','name':'Elon Musk',
                'public_channels':['x','official_company','video','press'],
                'asset_exposure':['TSLA','NQ','QQQ','BTC','DOGE','AI','SPACE'],
                'topics':['tesla','ai','space','crypto','technology'],
            },
        },
        'role_buckets': {
            'central_bank_leadership': {'discover_dynamically':True,'topics':['rates','inflation','liquidity']},
            'treasury_and_economic_officials': {'discover_dynamically':True,'topics':['fiscal','debt','currency','sanctions']},
            'mega_cap_technology_leadership': {'discover_dynamically':True,'topics':['ai','semiconductors','cloud','devices']},
            'semiconductor_leadership': {'discover_dynamically':True,'topics':['chips','ai','export_controls','capacity']},
            'energy_leadership': {'discover_dynamically':True,'topics':['oil','gas','power','commodities']},
            'crypto_ecosystem_leadership': {'discover_dynamically':True,'topics':['bitcoin','stablecoins','exchanges','regulation']},
        }
    }


def select_watchlist(registry, assets):
    wanted={str(a).upper() for a in assets}
    rows=[]
    for entity in registry.get('entities',{}).values():
        exposures={str(x).upper() for x in entity.get('asset_exposure',[])}
        if exposures & wanted:
            rows.append(dict(entity))
    return rows
