import pytest
from oracle.firewall import assert_no_execution_authority,ExecutionAuthorityError,research_envelope

def test_firewall_rejects_execution_authority():
    assert_no_execution_authority({'production_authorized':False,'research_note':'position sizing experiment'})
    with pytest.raises(ExecutionAuthorityError): assert_no_execution_authority({'production_authorized':True})
    with pytest.raises(ExecutionAuthorityError): assert_no_execution_authority({'order_id':'123'})
    env=research_envelope({'x':1},schema='x',purpose='research'); assert env['production_authorized'] is False
