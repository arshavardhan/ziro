"""Deterministic synthetic regression evaluation, not live LLM accuracy."""
import json
import subprocess
import sys
import tempfile
from datetime import datetime,timezone
import argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.deps')]
import config
from tools.ast_tool import analyze
from tools.similarity_tool import indicators
from tools.pytest_tool import parse_output,run
from tools.git_tool import history
from tools.github_tool import git
from core.guardrails import validate_url,safe_file
from security.signing import sign,verify
from agents.viva_evaluator import weighted,WEIGHTS
from scripts.create_demo_repo import create
from evaluation.metrics import summarize
from database.migrations import migrate
from database import repositories
from services.credential_service import issue
from core.exceptions import AppError

def execute(case,root):
    kind=case['kind']
    if kind in {'implementation','documentation'}:
        evidence=analyze({'a.py' if kind=='implementation' else 'README.md':case['source']},'a'*40)
        return any(e['kind'] in {'function','method'} and e['state']=='IMPLEMENTED' for e in evidence)
    if kind=='test_output':
        return parse_output(case['output'],case['exit_code'],3,.2,[])['status']
    if kind=='missing_tests':
        return run(root,{},[])['status']
    if kind in {'url','path'}:
        try:
            validate_url(case['value']) if kind=='url' else safe_file(root,case['value'])
            return True
        except ValueError:
            return False
    if kind=='duplicate':
        source='def f(xs):\n    total=0\n    for x in xs:\n        total+=x*x\n    return total\n'
        return bool(indicators({'a.py':source,'b.py':source.replace('def f','def g')}))
    if kind=='viva':
        return weighted({key:case['score'] for key in WEIGHTS})
    if kind in {'large_commit','incremental'}:
        if kind=='large_commit':
            repo=root/case['id']
            repo.mkdir()
            git(repo,'init')
            git(repo,'config','user.name','Synthetic Evaluation')
            git(repo,'config','user.email','synthetic@example.invalid')
            (repo/'large.py').write_text('\n'.join(f'v_{i} = {i}' for i in range(1100)),encoding='utf-8')
            git(repo,'add','large.py')
            git(repo,'commit','-m','Synthetic large initial introduction')
        else:
            repo=create(root/case['id'])
        summary=history(repo,git(repo,'rev-parse','HEAD').strip())
        return bool(summary['anomalies']) if kind=='large_commit' else summary['commit_count']
    if kind=='approval':
        migrate()
        session=repositories.create({'github_url':'https://github.com/synthetic/test','candidate_id':'SYNTHETIC','claimed_skills':['Python']})
        try:
            issue(session['session_id'])
            return True
        except AppError:
            return False
    if kind=='credential':
        secret='synthetic-evaluation-secret-'*2
        payload={'credential_id':'SYNTHETIC','signature_algorithm':'HMAC-SHA256','verified_skills':['Python']}
        payload['signature']=sign(payload,secret)
        if case['tamper']:
            payload['verified_skills'].append('Unsupported')
        return verify(payload,secret)
    raise ValueError('Unknown evaluation case')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',help='Execute one original case independently by ID')
    args=parser.parse_args()
    cases=json.loads((ROOT/'evaluation/test_cases.json').read_text())
    if args.case:
        cases=[c for c in cases if c['id']==args.case]
        if not cases:
            parser.error('Unknown case ID')
    results=[]
    original_db=config.DB_PATH
    with tempfile.TemporaryDirectory(prefix='skillproof-evaluation-') as temporary:
        root=Path(temporary)
        config.DB_PATH=root/'evaluation.sqlite3'
        try:
            for case in cases:
                try:
                    actual=execute(case,root)
                    results.append(dict(case,actual=actual,passed=actual==case['expected'],evaluated_at=datetime.now(timezone.utc).isoformat(),failure_details=None if actual==case['expected'] else 'Actual outcome did not match expected outcome'))
                except Exception as exc:
                    results.append(dict(case,actual=None,passed=False,error=type(exc).__name__,evaluated_at=datetime.now(timezone.utc).isoformat(),failure_details=str(exc)))
        finally:
            config.DB_PATH=original_db
    report={'label':'SYNTHETIC DETERMINISTIC EVALUATION — not a live LLM accuracy benchmark','evaluation_type':'SYNTHETIC_REGRESSION','evaluated_at':datetime.now(timezone.utc).isoformat(),'metrics':summarize(results),'cases':results,'real_world_accuracy_claim':False}
    output=ROOT.parent/'artifacts'
    output.mkdir(exist_ok=True)
    output=output/'evaluation-runs'
    output.mkdir(exist_ok=True)
    (output/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    migrate()
    from services.evaluation_service import register
    register(report)
    print(json.dumps(report['metrics'],indent=2))
    if not all(r['passed'] for r in results):
        raise SystemExit(1)

if __name__=='__main__':
    main()
