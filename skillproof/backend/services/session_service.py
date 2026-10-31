from agents import orchestrator,viva_evaluator
from database import repositories as memory
from core.state_machine import transition
from core.exceptions import AppError
from services.scoring_service import calculate,eligible

def answer(sid,request):
    with orchestrator.locks[sid]:
        data=memory.get(sid)
        if data['current_status']!='VIVA_PENDING':
            raise AppError('Session is not accepting viva answers')
        q=next((q for q in data['viva_questions'] if q['question_id']==request.question_id),None)
        if not q:
            raise AppError('Question not found',404,'NOT_FOUND')
        if request.question_id in data['viva_responses']:
            raise AppError('Question already answered')
        evaluation=orchestrator.llm(data,'viva_evaluator','EVALUATE_ANSWER',viva_evaluator.run,q,request.answer,data['code_evidence'])
        follow=None
        if evaluation['incomplete'] and not q['parent_question_id']:
            follow=dict(q,question_id=q['question_id']+'-followup',question=evaluation['follow_up_question'],parent_question_id=q['question_id'])
            data['viva_questions'].append(follow)
        result=dict(question_id=request.question_id,answer=request.answer,evaluation=evaluation,weighted_score=viva_evaluator.weighted(evaluation),follow_up=follow,current_status='VIVA_PENDING')
        data['viva_responses'][request.question_id]=result
        if all(q['question_id'] in data['viva_responses'] for q in data['viva_questions']):
            transition(data,'APPROVAL_PENDING')
        result['current_status']=data['current_status']
        calculate(data)
        events=[('viva_answers',result)]
        if follow:
            events.append(('viva_questions',follow))
        memory.record(data,'viva','OBSERVE',{'question_id':request.question_id,'weighted_score':result['weighted_score']},events=events)
        return result

def approve(sid,request):
    with orchestrator.locks[sid]:
        data=memory.get(sid)
        if data['current_status'] not in {'VIVA_PENDING','APPROVAL_PENDING','APPROVED'}:
            raise AppError('Session cannot be reviewed in its current state')
        skills=[]
        if request.approved:
            skills,errors=eligible(data)
            if errors:
                raise AppError('; '.join(errors))
        transition(data,'APPROVED' if request.approved else 'REJECTED')
        data['approval_status']='approved' if request.approved else 'rejected'
        data['approval']=dict(approval_status=data['approval_status'],current_status=data['current_status'],reviewer=request.reviewer,reason=request.reason,timestamp=memory.now())
        for skill,score in data['skill_scores'].items():
            score['verdict']='VERIFIED' if skill in skills else ('REJECTED' if not request.approved else score['verdict'])
        memory.record(data,'human_reviewer','APPROVAL',data['approval'],events=[('approval_records',data['approval'])])
        return data['approval']

def report(sid):
    data=memory.get(sid)
    from services.provenance_service import decorate
    data=decorate(data)
    skills,errors=eligible(data)
    if data['approval_status']!='approved':
        errors=errors+['Explicit human approval missing']
    sections={
        'A_repository_identity':data['baseline']['repository'] if data['baseline'] else {'url':data['github_url'],'commit_sha':data['repository_commit_sha']},
        'B_repository_analysis':{'measurements':data['baseline']['analysis'] if data['baseline'] else None,'snapshot':data['repository_snapshot']},
        'C_git_history':data['commit_summary'],
        'D_testing':{'test_discovery':data['test_discovery'],'test_execution':data['test_execution']},
        'E_skill_assessment':list(data['skill_scores'].values()),
        'F_technical_viva':{'questions':data['viva_questions'],'answers':data['viva_responses']},
        'G_evaluation_limitations':data['synthetic_evaluation'],
        'H_overall_assessment':{'scope':'Available repository and interview evidence, not the candidate\'s entire professional capability.',
            'demonstrated_capabilities':[s for s,v in data['skill_scores'].items() if v.get('status')=='IMPLEMENTED'],
            'unverified_capabilities':[s for s in data['claimed_skills'] if s not in data['skill_scores'] or data['skill_scores'][s].get('status')=='UNVERIFIED'],
            'missing_evidence':data['missing_evidence'],'limitations':data['limitations']},
        'I_credential_status':{'status':'ISSUED' if data['current_status']=='ISSUED' else data['approval_status'].upper()}}
    return dict(session_id=sid,current_status=data['current_status'],repository_commit_sha=data['repository_commit_sha'],
        baseline=data['baseline'],test_discovery=data['test_discovery'],test_execution=data['test_execution'],synthetic_evaluation=data['synthetic_evaluation'],sections=sections,stop_reason=data.get('stop_reason'),
        skill_report=list(data['skill_scores'].values()),evidence_references=data['code_evidence'],test_results=data['test_results'],
        git_findings=data['commit_summary'],similarity_findings=data['similarity_findings'],viva_evaluation=data['viva_responses'],
        missing_evidence=list(dict.fromkeys(data['missing_evidence']+[m for a in data['assessments'] for m in a['missing_evidence']])),
        limitations=data['limitations'],approval_status=data['approval_status'],eligible_skills=skills,blocking_reasons=errors,
        resume_info=data.get('resume_info'),resume_verification=data.get('resume_verification'))
