#!/usr/bin/env python3
"""Negotiate a provider adapter against runtime transport and credential support."""

TRANSPORT_ORDER = ["native_tool", "mcp_http", "mcp_stdio", "rest", "browser"]


def negotiate_adapter(provider, runtime):
    provider_transports = set(provider.get("transports", []))
    runtime_transports = set(runtime.get("supported_transports", []))
    candidates = [t for t in TRANSPORT_ORDER if t in provider_transports and t in runtime_transports]
    if not candidates:
        return {"compatible": False, "transport": None, "reason": "transport_unavailable"}

    auth_modes = set(provider.get("auth_modes", ["none"]))
    credentials = set(runtime.get("credential_modes", ["none"]))
    if "none" not in auth_modes and not auth_modes.intersection(credentials):
        return {"compatible": False, "transport": candidates[0], "reason": "auth_unavailable"}

    selected_auth = "none" if "none" in auth_modes else sorted(auth_modes.intersection(credentials))[0]
    return {"compatible": True, "transport": candidates[0], "auth_mode": selected_auth, "reason": None}
