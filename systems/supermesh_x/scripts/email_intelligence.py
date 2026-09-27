"""Normalize user-authorized email into SuperMesh private intelligence records."""

from __future__ import annotations

from typing import Any, Dict


def normalize_message(raw: Dict[str, Any]) -> Dict[str, Any]:
    attachments = []
    for item in raw.get("attachments", []) or []:
        attachments.append({
            "filename": item.get("filename"),
            "mime_type": item.get("mime_type") or item.get("mimeType"),
            "attachment_id": item.get("attachment_id"),
        })
    return {
        "message_id": raw.get("id") or raw.get("message_id"),
        "thread_id": raw.get("thread_id"),
        "sender": raw.get("from") or raw.get("sender"),
        "subject": raw.get("subject", ""),
        "published_time": raw.get("timestamp") or raw.get("published_time"),
        "body": raw.get("body", ""),
        "attachments": attachments,
        "source_class": "user_authorized_private",
        "exportable_to_public_providers": False,
    }


def classify_message(message: Dict[str, Any]) -> Dict[str, bool]:
    text = f"{message.get('subject','')} {message.get('body','')}".lower()
    return {
        "newsletter": any(k in text for k in ("substack", "newsletter", "new post from")),
        "market_alert": any(k in text for k in ("tradingview alert", "market alert", "condition triggered")),
        "broker_notice": any(k in text for k in ("broker", "order filled", "execution notice", "trade confirmation")),
    }
