"""Regression over the downloaded fixed snapshot; no candidate code is executed."""
from pathlib import Path
import pytest
import config
from services.repository_service import inspect_snapshot
from services.evidence_service import build

def test_entropy_to_trust_and_planned_wrapper():
    root=config.ROOT/'workspaces/aegis-fixed'
    if not root.exists():
        pytest.skip('Optional fixed AegisAI snapshot is not present')
    _,files,snapshot=inspect_snapshot(root,'https://github.com/arshavardhan/AegisAi')
    evidence,graph=build(files,snapshot['commit_sha'])
    entropy=next(e for e in evidence if e['symbol']=='EntropyEstimator.compute')
    trust=next(e for e in evidence if e['symbol']=='TrustScorer.compute')
    assert any(e['source']==entropy['evidence_id'] and e['target']==trust['evidence_id'] and e['relation']=='PASSES_VALUE:entropy' for e in graph)
    planned=next(e for e in evidence if e['symbol']=='OpenAIWrapper.embedding')
    assert planned['state']=='PLANNED'
    partial=next(e for e in evidence if e['symbol']=='OpenAIWrapper.predict_proba')
    assert partial['state']=='PARTIALLY_IMPLEMENTED'
