from scripts.email_intelligence import normalize_message, classify_message


def test_normalize_message_preserves_private_provenance_and_attachment_metadata():
    raw = {
        'id': 'm1', 'thread_id': 't1', 'from': 'writer@example.com',
        'subject': 'Macro update', 'timestamp': '2026-09-24T20:00:00Z',
        'body': 'CPI reaction and rates discussion',
        'attachments': [{'filename': 'report.pdf', 'mime_type': 'application/pdf'}],
    }
    msg = normalize_message(raw)
    assert msg['source_class'] == 'user_authorized_private'
    assert msg['message_id'] == 'm1'
    assert msg['attachments'][0]['filename'] == 'report.pdf'
    assert msg['exportable_to_public_providers'] is False


def test_classify_message_detects_newsletter_market_alert_and_broker_notice():
    assert classify_message({'subject':'New post from Macro Desk','body':'Read this Substack newsletter'})['newsletter']
    assert classify_message({'subject':'TradingView Alert: NQ cross','body':'condition triggered'})['market_alert']
    assert classify_message({'subject':'Broker execution notice','body':'order filled'})['broker_notice']
