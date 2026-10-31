"""Append-only measurement artifacts; legacy session JSON is never rewritten here."""
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime,timezone
import config
from database.connection import connect
from schemas.provenance import TestDiscovery,TestExecution

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def testing(data):
    result=data.get('test_results') or {}
    completed=bool(data.get('_checkpoint',{}).get('tests') or data.get('repository_commit_sha') and result.get('reason') or result.get('execution_record'))
    discovery=TestDiscovery(status='COMPLETED' if completed else 'NOT_ATTEMPTED',definitions_discovered=result.get('discovered_tests',0)).model_dump()
    record=result.get('execution_record')
    if record:
        execution=TestExecution.model_validate(record).model_dump()
    elif result.get('execution')=='PERFORMED':
        # Compatibility projection: keep historical result provenance explicit.
        status={'TIMEOUT':'TIMED_OUT'}.get(result.get('status'),result.get('status','ERROR'))
        counts=[result.get('passed'),result.get('failed')]
        execution=TestExecution(status=status,tests_executed=sum(counts) if all(v is not None for v in counts) else None,
            tests_passed=counts[0],tests_failed=counts[1],tests_skipped=result.get('skipped'),reason=result.get('reason'),
            counts_source='LEGACY_EXECUTION_RESULT').model_dump()
    else:
        reason=result.get('reason')
        execution=TestExecution(status='NOT_PERFORMED' if completed else 'NOT_ATTEMPTED',reason='Docker unavailable' if reason and reason.startswith('Docker unavailable') else reason,
            capability_check=result.get('capability_check')).model_dump()
    return discovery,execution

def get_baseline(sid):
    with connect() as db:
        row=db.execute('SELECT data FROM baseline_records WHERE session_id=? ORDER BY created_at LIMIT 1',(sid,)).fetchone()
    return json.loads(row['data']) if row else None

def freeze_baseline(data,legacy=False):
    existing=get_baseline(data['session_id'])
    if existing:
        return existing
    snap=data.get('repository_snapshot')
    if not snap:
        return None
    discovery,execution=testing(data)
    owner,name=data['github_url'].rstrip('/').split('/')[-2:]
    versions={}
    if not legacy:
        versions={'python':platform.python_version()}
        for package in ['radon','fastapi','pydantic']:
            try:
                versions[package]=importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package]=None
    version=None if legacy else config.ANALYZER_VERSION
    with connect() as db:
        rows=db.execute('SELECT data FROM baseline_records ORDER BY created_at DESC').fetchall()
        previous=next((json.loads(r['data']) for r in rows if json.loads(r['data'])['repository']['url']==data['github_url']),None)
        kind='ORIGINAL_BASELINE' if not previous else ('NEW_COMMIT' if previous['repository']['commit_sha']!=data['repository_commit_sha'] else ('NEW_ANALYZER_VERSION' if previous['provenance']['analyzer_version']!=version else 'REPEATED_SAME_COMMIT'))
        result=dict(assessment_id=data['session_id'],candidate_id=data['candidate_id'],record_kind=kind,prior_assessment_id=previous['assessment_id'] if previous else None,
            repository=dict(url=data['github_url'],owner=snap.get('owner') or owner,name=snap.get('name') or name,branch=snap.get('default_branch'),commit_sha=data['repository_commit_sha'],clone_timestamp=snap.get('cloned_at')),
            analysis=dict(text_files_analyzed=len(snap['files']),source_findings=len({e['evidence_id'] for e in data['code_evidence']}),git_commits_discovered=data['commit_summary']['commit_count'],
                test_definitions_discovered=discovery['definitions_discovered'],test_execution_status=execution['status'],test_execution_reason=execution['reason']),
            provenance=dict(analysis_type='STATIC_REPOSITORY_ANALYSIS',analyzer_version=version,configuration_version=None if legacy else config.CONFIG_VERSION,
                timestamp=data['agent_steps'][0]['timestamp'] if legacy and data['agent_steps'] else timestamp(),snapshot_timestamp=snap['captured_at'],tool_versions=versions,
                inclusion_rules=['Text files within configured inventory and file-size limits; Python AST analysis'],
                exclusion_rules=['Binaries, symlinks, submodules, .git, environment/secret files, oversized files'],
                configuration={} if legacy else dict(max_files=config.MAX_FILES,max_file_bytes=config.MAX_FILE_BYTES,max_repo_bytes=config.MAX_REPO_BYTES,weights=config.SCORE_WEIGHTS),
                unavailable_fields=['clone_timestamp','default_branch','analyzer_version','configuration_version','tool_versions'] if legacy else [],
                original_session_sha256=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()))
        db.execute('INSERT OR IGNORE INTO baseline_records(assessment_id,session_id,data) VALUES (?,?,?)',(data['session_id'],data['session_id'],json.dumps(result)))
    return result

def enrich_evidence(data):
    links={e['evidence_id']:[] for e in data['code_evidence']}
    for assessment in data.get('assessments',[]):
        for ref in set(assessment['supporting_evidence']):
            if ref in links:
                links[ref].append(assessment['skill'])
    original=data.get('_analyzer_version') is None
    for e in data['code_evidence']:
        e.update(assessment_id=data['session_id'],candidate_id=data['candidate_id'],claimed_skills=links[e['evidence_id']],
            evidence_type='DOCUMENTATION' if e['kind']=='documentation' else ('TEST_DISCOVERY' if '/test' in e['file'] or e['file'].startswith('test') else 'CODE_IMPLEMENTATION'),
            collection_tool=e.get('collection_tool') or (None if original else 'python_ast_radon' if e['file'].endswith('.py') else 'source_reader'),
            collected_at=e.get('collected_at') or data.get('_source_collected_at'),
            raw_observation={'symbol':e['symbol'],'state':e['state'],'observed_facts':e['observed_facts']},
            interpretation=e.get('interpretation'),evidence_strength='STATIC_OBSERVATION',verification_status=e['state'])
    return data

def decorate(data):
    from services.evaluation_service import disclosure
    data['baseline']=get_baseline(data['session_id'])
    data['test_discovery'],data['test_execution']=testing(data)
    data['synthetic_evaluation']=disclosure()
    return enrich_evidence(data)

def preserve_legacy():
    with connect() as db:
        rows=db.execute('SELECT data FROM verification_sessions').fetchall()
    for row in rows:
        data=json.loads(row['data'])
        if data.get('repository_snapshot') and not data.get('_analyzer_version'):
            freeze_baseline(data,legacy=True)
