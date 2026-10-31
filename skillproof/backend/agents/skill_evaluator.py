from agents.llm import reason
from schemas.agents import Assessments
from services.evidence_service import implementation_evidence
from core.exceptions import AppError

def compact(evidence):
    from collections import defaultdict
    groups=defaultdict(list)
    for item in sorted(evidence,key=lambda e:(e['kind'] not in {'function','method'},e['state']!='IMPLEMENTED')):
        groups[item['file']].append(item)
    selected=[]
    while groups and len(selected)<60:
        for file in list(groups):
            if len(selected)>=60:
                break
            e=groups[file].pop(0)
            selected.append({**e,'source':e['source'] if len(e['source'])<=1400 else e['source'][:300]+'\n# ... excerpt omitted ...\n'+e['source'][-1000:],
                             'docstring':(e.get('docstring') or '')[:200]})
            if not groups[file]:
                del groups[file]
    return selected

def run(skills,evidence,graph,tests,history):
    result = reason('Evaluate every claimed skill exactly once. Cite only supplied evidence IDs. Documentation, imports, stubs and test code alone do not establish production implementation. Explain architecture via relationships. Never return VERIFIED before human review. Use null for unavailable evidence, zero for observed negative evidence.',
        {'skills':skills,'evidence':compact(evidence),'relationships':graph[:100],'tests':tests,'history':{'commit_count':history['commit_count'],'limitations':history['limitations']}},Assessments)['assessments']
    if sorted(a['skill'] for a in result)!=sorted(skills):
        raise AppError('Model skill set did not match claims',502,'INVALID_ASSESSMENT')
    valid = {e['evidence_id'] for e in implementation_evidence(evidence)}
    known = {e['evidence_id'] for e in evidence}
    for item in result:
        original = item['supporting_evidence']
        item['supporting_evidence'] = list(dict.fromkeys(ref for ref in original if ref in known))
        if not set(original)&valid or any(ref not in known for ref in original):
            item.update(verdict='INSUFFICIENT_EVIDENCE',implementation_score=None,architecture_score=None)
            item['limitations'].append('No validated production implementation citation, or invalid model citation.')
        elif item['verdict']=='VERIFIED':
            item['verdict']='PARTIALLY_VERIFIED'
    return result
