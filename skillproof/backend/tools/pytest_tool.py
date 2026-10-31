import ast
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from schemas.evidence import TestResult
from security.sandbox import docker_command
from core.guardrails import redact
from tools.ast_tool import is_test
from datetime import datetime,timezone

def capability():
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'isolation':'restricted_docker','available':False,'reason':'Docker unavailable','status':'NOT_PERFORMED'}
    if not shutil.which('docker'):
        return result
    import config
    try:
        for command in [['docker','info','--format','{{.ServerVersion}}'],['docker','image','inspect',config.TEST_IMAGE,'--format','{{.Id}}']]:
            checked=subprocess.run(command,capture_output=True,timeout=10)
            if checked.returncode:
                return dict(result,reason='Docker daemon or trusted test image unavailable',status='BLOCKED')
    except (OSError,subprocess.TimeoutExpired):
        return dict(result,reason='Docker capability check failed or timed out',status='BLOCKED')
    return dict(result,available=True,reason=None,status='READY')

def discover(files):
    count = 0
    for file,source in files.items():
        if not file.endswith('.py') or not is_test(file):
            continue
        try:
            tree = ast.parse(source)
            count += sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test') for n in ast.walk(tree))
        except SyntaxError:
            pass
    return count

def parse_output(output,exit_code,discovered,runtime,edges):
    # Only parse pytest's final summary, never arbitrary earlier print statements.
    summary = next((line for line in reversed(output.splitlines()) if re.search(r'\b\d+ (passed|failed|skipped|error)',line)), '')
    counts = {key:None for key in ['passed','failed','skipped','collection_errors']}
    if summary:
        for key,word in [('passed','passed'),('failed','failed'),('skipped','skipped'),('collection_errors','error')]:
            match = re.search(r'(\d+) '+word,summary)
            counts[key] = int(match[1]) if match else 0
    return TestResult(execution='PERFORMED',status='PASSED' if exit_code==0 else ('FAILED' if exit_code==1 else 'ERROR'),
        discovered_tests=discovered,collected_tests=sum(counts[k] for k in ['passed','failed','skipped']) if summary else None,
        **counts,runtime_seconds=round(runtime,3),exit_code=exit_code,output=redact(output),test_to_module=edges,
        limitations=['Counts parsed from pytest summary; tests may be parametrized beyond static discovery.',
                      'Untrusted repository tests can manipulate output; not independently attested coverage.']).model_dump(mode='json')

def _run(root,files,edges):
    discovered = discover(files)
    links = [e for e in edges if e['relation']=='TEST_IMPORTS']
    base = TestResult(discovered_tests=discovered,test_to_module=links,limitations=['Static discovery counts test definitions, not parametrized runtime cases.'])
    if not discovered:
        return base.model_copy(update={'reason':'No test definitions discovered'}).model_dump(mode='json')
    if not shutil.which('docker'):
        return base.model_copy(update={'reason':'Docker unavailable; adequate isolation unavailable, execution NOT PERFORMED'}).model_dump(mode='json')
    name = 'skillproof-'+uuid.uuid4().hex
    start = time.monotonic()
    try:
        with tempfile.TemporaryFile() as output:
            with subprocess.Popen(docker_command(root,name),stdout=output,stderr=output) as process:
                while process.poll() is None:
                    if time.monotonic()-start>60 or output.tell()>1_000_000:
                        process.kill()
                        process.wait()
                        return base.model_copy(update={'execution':'PERFORMED','status':'TIMEOUT','reason':'Runtime or output limit exceeded','runtime_seconds':round(time.monotonic()-start,3)}).model_dump(mode='json')
                    time.sleep(.1)
                # Keep the tail because pytest counts appear at the end.
                size = output.tell()
                output.seek(max(0,size-16000))
                text = output.read(16000).decode(errors='replace')
                if process.returncode in {125,126,127}:
                    return base.model_copy(update={'reason':'Docker image/runtime unavailable; execution NOT PERFORMED','output':redact(text)}).model_dump(mode='json')
                return parse_output(text,process.returncode,discovered,time.monotonic()-start,links)
    except OSError:
        return base.model_copy(update={'reason':'Docker could not start; execution NOT PERFORMED'}).model_dump(mode='json')
    finally:
        try:
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired):
            pass

def run(root,files,edges):
    check=capability()
    if not check['available']:
        result=TestResult(discovered_tests=discover(files),reason=check['reason'],test_to_module=[e for e in edges if e['relation']=='TEST_IMPORTS']).model_dump(mode='json')
        record={'status':check['status'],'tests_executed':0,'tests_passed':0,'tests_failed':0,'tests_skipped':0,'reason':check['reason'],
                'execution_id':None,'capability_check':check,'counts_source':'NO_EXECUTION_RECORD'}
    else:
        result=_run(root,files,edges)
        performed=result['execution']=='PERFORMED'
        status={'TIMEOUT':'TIMED_OUT'}.get(result['status'],result['status'])
        if not performed and result.get('reason','').startswith('Docker'):
            status='BLOCKED'
        if status=='FAILED' and (result.get('passed') or 0)>0:
            status='PARTIALLY_PASSED'
        counts=[result.get('passed'),result.get('failed')]
        record={'status':status,'tests_executed':sum(counts) if all(v is not None for v in counts) else (None if performed else 0),
            'tests_passed':result.get('passed') if performed else 0,'tests_failed':result.get('failed') if performed else 0,'tests_skipped':result.get('skipped') if performed else 0,
            'reason':result.get('reason'),'execution_id':str(uuid.uuid4()) if performed else None,'capability_check':check,
            'counts_source':'PYTEST_OUTPUT' if performed else 'NO_EXECUTION_RECORD'}
    result['capability_check']=check
    result['execution_record']=record
    return result
