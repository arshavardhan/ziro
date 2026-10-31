import json
import uuid
import config
from agents.orchestrator import locks
from database.connection import connect
from database import repositories as memory
from security.signing import sign,verify
from services.scoring_service import eligible
from core.state_machine import transition
from core.exceptions import AppError
from schemas.credentials import Credential

def get(cid):
    with connect() as db:
        row=db.execute('SELECT data FROM credentials WHERE id=?',(cid,)).fetchone()
    if not row:
        raise AppError('Credential not found',404,'NOT_FOUND')
    return json.loads(row['data'])

def issue(sid):
    with locks[sid]:
        data=memory.get(sid)
        if data['approval_status']!='approved' or data['current_status'] not in {'APPROVED','ISSUED'}:
            raise AppError('Explicit human approval required; rejection blocks issuance')
        skills,errors=eligible(data)
        if errors:
            raise AppError('; '.join(errors))
        if len(config.SIGNING_SECRET)<32:
            raise AppError('Configure a signing secret of at least 32 characters',503,'NOT_CONFIGURED')
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT data FROM credentials WHERE session_id=?',(sid,)).fetchone()
            if row:
                payload=json.loads(row['data'])
            else:
                from services.provenance_service import get_baseline,testing
                baseline=get_baseline(sid)
                _,execution=testing(data)
                payload=dict(credential_id=str(uuid.uuid4()),candidate_id=data['candidate_id'],repository_url=data['github_url'],
                    repository_commit_sha=data['repository_commit_sha'],verified_skills=skills,skill_scores={s:data['skill_scores'][s] for s in skills},
                    evidence_references={s:data['skill_scores'][s]['supporting_evidence'] for s in skills},
                    viva_summary={qid:r['weighted_score'] for qid,r in data['viva_responses'].items()},issued_timestamp=memory.now(),
                    issuer='SkillProof AI',signature_algorithm='HMAC-SHA256',assessment_date=baseline['provenance']['timestamp'] if baseline else None,
                    evidence_summary={s:{'supporting_evidence':data['skill_scores'][s]['supporting_evidence'],'evidence_coverage':data['skill_scores'][s]['evidence_coverage']} for s in skills},
                    test_execution=execution,assessment_limitations=list(dict.fromkeys(data['limitations']+[
                        'Evaluates available evidence, not total professional capability.',
                        'HMAC-SHA256 uses a shared secret, not public-key signature verification.',
                        'Test execution: '+execution['status']+('. '+execution['reason'] if execution['reason'] else '')])))
                # Normalize all schema types before signing; API serialization must preserve bytes.
                payload=Credential.model_validate(dict(payload,signature='')).model_dump(mode='json')
                payload['signature']=sign(payload,config.SIGNING_SECRET)
                db.execute('INSERT INTO credentials VALUES (?,?,?)',(payload['credential_id'],sid,json.dumps(payload)))
            if data['current_status']!='ISSUED':
                event=dict(event_id=str(uuid.uuid4()),sequence=len(data['agent_steps'])+1,timestamp=memory.now(),agent='credential',phase='ISSUE',status='completed',observation={'credential_id':payload['credential_id']})
                data['agent_steps'].append(event)
                db.execute('INSERT INTO agent_observations(session_id,data) VALUES (?,?)',(sid,json.dumps(event)))
            transition(data,'ISSUED')
            db.execute('UPDATE verification_sessions SET status=?,data=? WHERE id=?',('ISSUED',json.dumps(data),sid))
        config.CREDENTIALS.mkdir(parents=True,exist_ok=True)
        path=config.CREDENTIALS/(payload['credential_id']+'.json')
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        temporary.replace(path)
        return payload

def verify_payload(payload):
    return dict(valid=verify(payload,config.SIGNING_SECRET),credential_id=payload.get('credential_id') if isinstance(payload.get('credential_id'),str) else None)
