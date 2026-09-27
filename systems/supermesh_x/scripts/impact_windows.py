#!/usr/bin/env python3
"""Event-study windows for high-frequency and swing market-impact analysis."""


def event_windows(style='intraday'):
    if style == 'swing':
        return {
            'pre_minutes':[(-60,0),(-30,0),(-10,0)],
            'post_minutes':[(0,1),(0,5),(0,15),(0,30),(0,60)],
            'post_days':[1,2,3,5],
        }
    return {
        'pre_minutes':[(-10,0),(-5,0),(-2,0),(-1,0)],
        'post_minutes':[(0,1),(0,2),(0,5),(0,10),(0,30),(0,60)],
        'post_days':[],
    }
