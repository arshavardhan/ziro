import json
import uuid
from datetime import datetime,timezone
from database.connection import connect
from database.models import EVENT_TABLES
from core.exceptions import AppError
from schemas.session import SessionResponse

def now():
    return datetime.now(timezone.utc).isoformat()

def create(request):
    import config
    sid = str(uuid.uuid4())
    resume_info = None
    if request.get('resume_text'):
        from services.resume_service import parse_resume
        resume_info = parse_resume(request['resume_text'], request.get('resume_filename'))
    elif request.get('resume_skills'):
        resume_info = {
            'candidate_name': None,
            'email': None,
            'phone': None,
            'github_url': None,
            'extracted_skills': request.get('resume_skills', []),
            'experience_summary': request.get('description'),
            'raw_text_length': 0,
            'filename': request.get('resume_filename'),
        }
    data = SessionResponse(
        session_id=sid,
        candidate_id=request['candidate_id'],
        github_url=request['github_url'],
        claimed_skills=request['claimed_skills'],
        current_status='QUEUED',
        resume_info=resume_info,
    ).model_dump(mode='json')
    data['_requested_sha'] = request.get('commit_sha')
    data['_checkpoint'] = {}
    data['_analyzer_version']=config.ANALYZER_VERSION
    data['_created_at']=now()
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO candidates VALUES (?)',(request['candidate_id'],))
        db.execute('INSERT INTO verification_sessions(id,candidate_id,status,data) VALUES (?,?,?,?)',(sid,request['candidate_id'],'QUEUED',json.dumps(data)))
        db.execute('INSERT INTO skill_claims(session_id,data) VALUES (?,?)',(sid,json.dumps(request['claimed_skills'])))
    return data

def get(sid):
    with connect() as db:
        row = db.execute('SELECT data FROM verification_sessions WHERE id=?',(sid,)).fetchone()
    if not row:
        raise AppError('Session not found',404,'NOT_FOUND')
    return json.loads(row['data'])

def save(data, events=()):
    with connect() as db:
        db.execute('UPDATE verification_sessions SET status=?,data=?,updated_at=? WHERE id=?',(data['current_status'],json.dumps(data),now(),data['session_id']))
        for table,payload in events:
            if table not in EVENT_TABLES:
                raise ValueError('Unknown memory table')
            db.execute(f'INSERT INTO {table}(session_id,data) VALUES (?,?)',(data['session_id'],json.dumps(payload)))

def record(data,agent,phase,observation,status='completed',events=()):
    event = dict(event_id=str(uuid.uuid4()),sequence=len(data['agent_steps'])+1,timestamp=now(),agent=agent,phase=phase,status=status,observation=observation)
    data['agent_steps'].append(event)
    save(data,[('agent_observations',event),*events])

def pending():
    from core.state_machine import IN_FLIGHT
    with connect() as db:
        rows = db.execute('SELECT id,status FROM verification_sessions').fetchall()
    return [row['id'] for row in rows if row['status'] in IN_FLIGHT]

def public(data):
    from services.provenance_service import decorate
    data=decorate(data)
    return SessionResponse.model_validate({k:v for k,v in data.items() if not k.startswith('_')})
