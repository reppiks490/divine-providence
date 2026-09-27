from scripts.private_source_policy import can_route_payload, redact_private_record


def test_private_payload_cannot_be_sent_to_public_provider_without_explicit_transform():
    record = {'source_class':'user_authorized_private','body':'private newsletter text','symbol':'NQ'}
    decision = can_route_payload(record, target_class='public_provider')
    assert decision['allowed'] is False
    assert decision['reason'] == 'private_to_public_blocked'


def test_redaction_can_emit_non_sensitive_derived_features_only():
    record = {'source_class':'user_authorized_private','body':'private text','symbol':'NQ','topic':'rates','sentiment':-0.5}
    redacted = redact_private_record(record, allow_fields=['symbol','topic','sentiment'])
    assert 'body' not in redacted
    assert redacted == {'symbol':'NQ','topic':'rates','sentiment':-0.5,'source_class':'derived_private_feature'}
