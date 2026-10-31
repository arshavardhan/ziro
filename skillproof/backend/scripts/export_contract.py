import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.deps')]
from main import app
from schemas.session import AnalyzeResponse,SessionResponse

output=ROOT.parent
schema=app.openapi()
(output/'openapi.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
(output/'schemas.json').write_text(json.dumps(schema['components']['schemas'],indent=2),encoding='utf-8')
examples=output/'examples'
examples.mkdir(exist_ok=True)
request={'github_url':'https://github.com/arshavardhan/AegisAi','candidate_id':'CAND-001','claimed_skills':['Python','Machine Learning'],
         'commit_sha':'79112160653cc38cdcbddaf578e29ecfbd58a70a'}
samples={'analyze-request':request,'analyze-response':AnalyzeResponse(session_id='example-session').model_dump(),
    'session-queued':SessionResponse(session_id='example-session',candidate_id='CAND-001',github_url=request['github_url'],claimed_skills=request['claimed_skills'],current_status='QUEUED').model_dump(mode='json'),
    'error':{'error':{'code':'INVALID_STATE','message':'Explicit human approval required; rejection blocks issuance','details':[]}}}
for name,sample in samples.items():
    (examples/(name+'.json')).write_text(json.dumps(sample,indent=2),encoding='utf-8')
print('Exported OpenAPI, exact JSON schemas and integration examples')
