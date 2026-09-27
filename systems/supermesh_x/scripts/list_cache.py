"""MCP list-result cache and list-change subscription normalization."""
VALID_SCOPES={'private','public'}

def normalize_list_cache(result, *, protocol_version, observed_at_ms, max_ttl_ms=300000, principal=None):
    modern = protocol_version == '2026-07-28'
    raw_ttl = result.get('ttlMs', 0 if modern else 0)
    try: ttl=max(0, min(int(raw_ttl), int(max_ttl_ms)))
    except (TypeError, ValueError): ttl=0
    scope=result.get('cacheScope', 'private')
    if scope not in VALID_SCOPES: scope='private'
    return {'protocol_version':protocol_version,'ttl_ms':ttl,'cache_scope':scope,
            'observed_at_ms':int(observed_at_ms),'fresh_until_ms':int(observed_at_ms)+ttl,
            'principal':principal if scope=='private' else None}

def cache_is_fresh(entry, *, now_ms, principal=None):
    if int(now_ms) >= int(entry['fresh_until_ms']): return False
    if entry.get('cache_scope')=='private' and entry.get('principal') is not None and principal != entry.get('principal'):
        return False
    return True

def subscription_policy(protocol_version, requested, *, advertised=None):
    if protocol_version != '2026-07-28':
        return {'transport':'legacy_unsolicited','listen_filter':None}
    advertised=advertised or {}
    keys=('tools','prompts','resources')
    filt={k: bool(requested.get(k)) and bool(advertised.get(k)) for k in keys}
    return {'transport':'subscriptions/listen','listen_filter':filt}
