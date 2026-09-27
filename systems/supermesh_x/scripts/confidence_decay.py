#!/usr/bin/env python3
"""Decay event confidence with age and unresolved contradictory evidence."""
from math import exp, log


def _c(v):
    return max(0.0,min(1.0,float(v)))


def decayed_confidence(base_confidence, age_minutes, conflict_strength=0.0, half_life_minutes=180.0):
    if age_minutes < 0:
        raise ValueError('age_minutes must be nonnegative')
    if half_life_minutes <= 0:
        raise ValueError('half_life_minutes must be positive')
    time_factor=exp(-log(2.0)*float(age_minutes)/float(half_life_minutes))
    conflict_factor=1.0-0.8*_c(conflict_strength)
    confidence=_c(base_confidence)*time_factor*conflict_factor
    return {
        'confidence':round(max(0.0,min(1.0,confidence)),6),
        'time_factor':round(time_factor,6),
        'conflict_factor':round(conflict_factor,6),
    }
