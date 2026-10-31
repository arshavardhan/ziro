import pytest
from tools.ast_tool import analyze
from services.evidence_service import build,implementation_evidence
from tools.similarity_tool import indicators
from tools.pytest_tool import parse_output,run

@pytest.mark.parametrize('source,state',[
    ('def f(x):\n    return x+1','IMPLEMENTED'),
    ('def f():\n    pass','PLANNED'),
    ('def f():\n    raise NotImplementedError()','PLANNED'),
    ('def f(x):\n    if x: return x\n    raise NotImplementedError()','PARTIALLY_IMPLEMENTED'),
    ('def f(x):\n    """Placeholder probability output."""\n    return [1]','PARTIALLY_IMPLEMENTED'),
])
def test_implementation_states(source,state):
    assert analyze({'a.py':source},'a'*40)[0]['state']==state

def test_documentation_is_not_implementation():
    assert not implementation_evidence(analyze({'README.md':'Advanced ML and testing planned'},'a'*40))

def test_empty_repository():
    assert build({},'a'*40)==([],[])

def test_line_references_and_graph():
    files={'a.py':'def f(x: int) -> int:\n    return x+1\n','test_a.py':'from a import f\ndef test_f():\n    assert f(1)==2\n'}
    evidence,edges=build(files,'a'*40)
    assert evidence[0]['line_start']==1 and evidence[0]['line_end']==2
    assert evidence[0]['type_hints']==['int','int']
    assert any(e['relation']=='CALLS' for e in edges)
    assert evidence[0]['test_references']==['test_a.py']

def test_duplicate_code():
    source='def first(xs):\n    value=0\n    for x in xs:\n        value+=x*x\n    return value\n'
    findings=indicators({'a.py':source,'b.py':source.replace('first','second')})
    assert findings[0]['similarity']==1
    assert findings[0]['measure']=='AST body fingerprint'

@pytest.mark.parametrize('text,code,status,passed,failed',[('3 passed in 0.1s',0,'PASSED',3,0),('1 failed, 2 passed in 0.1s',1,'FAILED',2,1),('1 error in 0.1s',2,'ERROR',0,0)])
def test_pytest_result_parser(text,code,status,passed,failed):
    result=parse_output(text,code,3,.1,[])
    assert (result['status'],result['passed'],result['failed'])==(status,passed,failed)

def test_missing_tests(tmp_path):
    result=run(tmp_path,{'a.py':'x=1'},[])
    assert result['execution']=='NOT_PERFORMED'
    assert result['passed'] is None
