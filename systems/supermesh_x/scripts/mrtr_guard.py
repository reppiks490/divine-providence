#!/usr/bin/env python3
"""Safety guards for MCP 2026-07-28 multi-round-trip and Tasks extension flows."""
from __future__ import annotations

MODERN_ERA = '2026-07-28'
DEPRECATED_MODERN = {'sampling/createMessage', 'roots/list'}
ALLOWED_INPUT_METHODS = {'elicitation/create'}


def validate_input_required(result, protocol_version=MODERN_ERA, round_number=1, max_rounds=10, max_requests=16):
    row = dict(result or {})
    if row.get('resultType') != 'input_required':
        return {'allowed': False, 'reason': 'not_input_required'}
    if not row.get('requestState'):
        return {'allowed': False, 'reason': 'missing_request_state'}
    if int(round_number) > int(max_rounds):
        return {'allowed': False, 'reason': 'mrtr_round_limit_exceeded'}
    reqs = dict(row.get('inputRequests') or {})
    if not reqs:
        return {'allowed': False, 'reason': 'missing_input_requests'}
    if len(reqs) > int(max_requests):
        return {'allowed': False, 'reason': 'too_many_input_requests'}
    for request in reqs.values():
        method = str((request or {}).get('method') or '')
        if str(protocol_version) >= MODERN_ERA and method in DEPRECATED_MODERN:
            return {'allowed': False, 'reason': 'deprecated_modern_input_request'}
        if method not in ALLOWED_INPUT_METHODS and str(protocol_version) >= MODERN_ERA:
            return {'allowed': False, 'reason': 'unsupported_input_request'}
    return {'allowed': True, 'reason': 'allowed', 'request_count': len(reqs)}


def build_resume_envelope(prior_result, responses):
    prior = dict(prior_result or {})
    known = set(dict(prior.get('inputRequests') or {}))
    supplied = dict(responses or {})
    return {
        'requestState': prior.get('requestState'),
        'inputResponses': {k: supplied[k] for k in known if k in supplied},
    }


def validate_task_descriptor(task, min_id_length=24):
    row = dict(task or {})
    task_id = str(row.get('taskId') or '')
    if len(task_id) < int(min_id_length):
        return {'allowed': False, 'reason': 'weak_or_missing_task_id', 'enumeration_allowed': False}
    if row.get('status') not in {'working','input_required','completed','failed','cancelled'}:
        return {'allowed': False, 'reason': 'invalid_task_status', 'enumeration_allowed': False}
    return {'allowed': True, 'reason': 'allowed', 'enumeration_allowed': False}
