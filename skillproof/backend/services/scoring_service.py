import config
from services.evidence_service import implementation_evidence

WEIGHTS = config.SCORE_WEIGHTS

def calculate(data):
    answers = data['viva_responses']
    base = [q for q in data['viva_questions'] if not q['parent_question_id']]
    viva = sum(answers[q['question_id']]['weighted_score'] for q in base)/5 if len(base)==5 and all(q['question_id'] in answers for q in base) else None
    by_id = {e['evidence_id']:e for e in data['code_evidence']}
    result = {}
    for item in data['assessments']:
        refs=list(dict.fromkeys(item['supporting_evidence']))
        missing=[ref for ref in refs if ref not in by_id or by_id[ref]['commit_sha']!=data['repository_commit_sha']]
        supporting = [by_id[ref] for ref in refs if ref not in missing]
        traceable=bool(supporting) and not missing
        test = data['test_results']
        count = sum(test.get(k) or 0 for k in ['passed','failed'])
        linked = any(e['test_references'] for e in supporting)
        test_score = 100*test['passed']/count if linked and test['execution']=='PERFORMED' and count and test['passed'] is not None else None
        factors = dict(implementation_score=item['implementation_score'] if traceable else None,test_score=test_score,architecture_score=item['architecture_score'] if traceable else None,
            git_score=min(100,data['commit_summary']['commit_count']*20) if data['commit_summary']['commit_count'] else None,viva_score=viva)
        coverage = sum(WEIGHTS[k] for k,v in factors.items() if v is not None)
        score = round(sum(WEIGHTS[k]*v for k,v in factors.items() if v is not None)/coverage,2) if coverage and traceable else None
        result[item['skill']] = dict(skill=item['skill'],score=score,**factors,evidence_coverage=coverage,
            verdict=('PARTIALLY_VERIFIED' if item['verdict']=='VERIFIED' else item['verdict']) if traceable else 'INSUFFICIENT_EVIDENCE',supporting_evidence=[e['evidence_id'] for e in supporting],
            status='IMPLEMENTED' if any(e['state']=='IMPLEMENTED' for e in supporting) else ('PARTIALLY_IMPLEMENTED' if any(e['state']=='PARTIALLY_IMPLEMENTED' for e in supporting) else 'UNVERIFIED'),
            traceability={'valid':traceable,'missing_evidence_ids':missing,'commit_sha':data['repository_commit_sha']},scoring_weights=WEIGHTS,
            evidence_dimensions={'repository_implementation':any(e['state']=='IMPLEMENTED' for e in supporting),'static_support':bool(supporting),
                'executed_tests':test_score is not None,'viva_demonstrated':viva is not None and viva>=config.MIN_VIVA},
            missing_evidence=item['missing_evidence'],limitations=item['limitations']+[
                'Heuristic score, not a calibrated probability. Git score describes repository progression, not candidate authorship.',
                'Test score is a repository-wide pass ratio applied only to statically linked modules; function coverage is unknown.',
                'Viva uses five base answers; follow-ups cannot erase weak original answers.'])
        if test['execution']!='PERFORMED':
            result[item['skill']]['missing_evidence']=list(dict.fromkeys(result[item['skill']]['missing_evidence']+['Test execution unavailable; no pass/fail or coverage conclusion.']))
    data['skill_scores']=result
    return result

def eligible(data,require_review_state=True):
    errors = []
    if require_review_state and data['current_status'] not in {'APPROVAL_PENDING','APPROVED','ISSUED'}:
        errors.append('Analysis, five base answers and all follow-ups must be completed')
    if not data.get('repository_commit_sha') or not data['_checkpoint'].get('analysis_complete'):
        errors.append('Pinned repository analysis is incomplete')
    if len([q for q in data['viva_questions'] if not q['parent_question_id']])!=5 or any(q['question_id'] not in data['viva_responses'] for q in data['viva_questions']):
        errors.append('All viva questions must be answered')
    valid = {e['evidence_id'] for e in implementation_evidence(data['code_evidence']) if e['state'] in {'IMPLEMENTED','TESTED'}}
    skills=[]
    for a in data['assessments']:
        s=data['skill_scores'].get(a['skill'],{})
        known={e['evidence_id'] for e in data['code_evidence'] if e['commit_sha']==data['repository_commit_sha']}
        if not a['supporting_evidence'] or any(ref not in known for ref in a['supporting_evidence']):
            continue
        if (a['verdict'] in {'PARTIALLY_VERIFIED','VERIFIED'} and a['confidence']>=.7 and set(a['supporting_evidence'])&valid
            and s.get('score') is not None and s['score']>=config.MIN_SCORE and s['evidence_coverage']>=55
            and s['viva_score'] is not None and s['viva_score']>=config.MIN_VIVA):
            skills.append(a['skill'])
    if not skills:
        errors.append('No skill meets evidence, confidence, coverage and viva criteria')
    return ([] if errors else skills),errors
