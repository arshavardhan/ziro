import hashlib
import json
from pathlib import Path
import config
from database.connection import connect

def register(report):
    serialized=json.dumps(report,sort_keys=True)
    eid='eval-'+hashlib.sha256(serialized.encode()).hexdigest()[:20]
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO evaluation_runs(evaluation_id,data) VALUES (?,?)',(eid,json.dumps(report)))
    return eid

def preserve_original():
    path=config.ROOT.parent/'artifacts/evaluation-results.json'
    if path.exists():
        register(json.loads(path.read_text(encoding='utf-8')))

def disclosure():
    with connect() as db:
        row=db.execute('SELECT evaluation_id,data FROM evaluation_runs ORDER BY created_at LIMIT 1').fetchone()
    if not row:
        return {'limitations':'Synthetic evaluation unavailable; no real-world accuracy claim.'}
    data=json.loads(row['data']); cases=data['cases']
    total=len(cases); passed=sum(c['passed'] for c in cases)
    metrics=data['metrics']['classification']; count=metrics['sample_count']
    return dict(evaluation_id=row['evaluation_id'],evaluation_type='SYNTHETIC_REGRESSION',total_cases=total,passed=passed,failed=total-passed,result='PASSED' if passed==total else 'FAILED',
        classification_metric_fixture_count=count,classification_metrics=metrics,real_world_accuracy_claim=False,evaluation_timestamp=data.get('evaluated_at'),
        limitations=f'{passed} of {total} synthetic evaluation cases passed. Classification metrics are calculated from {count} small fixtures and are intended for internal regression testing, not as estimates of real-world accuracy. The sample does not establish generalization.')
