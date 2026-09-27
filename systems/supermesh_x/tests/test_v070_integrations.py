from pathlib import Path
import json
from scripts.integration_hub import select_integrations
ROOT=Path(__file__).resolve().parents[1]


def test_gmail_and_finances_are_routable_private_integrations_when_ready():
    mail=select_integrations('communications.email.search', {'gmail':'ready'})
    fin=select_integrations('portfolio.holdings', {'finances':'ready'})
    assert mail['selected'][0]['id']=='gmail'
    assert fin['selected'][0]['id']=='finances'
    assert mail['selected'][0]['permission_class']=='private_read_write_gated'
    assert fin['selected'][0]['permission_class']=='private_read_write_gated'


def test_private_integration_configs_declare_no_public_raw_export():
    g=json.loads((ROOT/'config/gmail-integration.json').read_text())
    f=json.loads((ROOT/'config/finances-integration.json').read_text())
    p=json.loads((ROOT/'config/private-source-boundary.json').read_text())
    assert g['raw_content_public_export']==False
    assert f['raw_financial_data_public_export']==False
    assert p['default_private_to_public']=='deny'
