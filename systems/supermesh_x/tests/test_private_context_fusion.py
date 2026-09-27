from scripts.private_context_fusion import fuse_public_event_with_private_context


def test_private_context_fusion_keeps_public_and_private_evidence_separate():
    public = {'event_id':'e1','topic':'hormuz','confidence':0.82,'evidence_ids':['pub1','pub2']}
    private = {'portfolio_id':'p1','overlay_score':-0.35,'evidence_ids':['priv1']}
    out = fuse_public_event_with_private_context(public, private)
    assert out['public_evidence_ids'] == ['pub1','pub2']
    assert out['private_evidence_ids'] == ['priv1']
    assert out['private_context_exportable'] is False
    assert out['combined']['event_id'] == 'e1'
