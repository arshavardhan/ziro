from collections import Counter
from agents.llm import reason
from agents.skill_evaluator import compact
from schemas.viva import Questions
from services.evidence_service import implementation_evidence
from core.exceptions import AppError

def run(evidence):
    eligible = implementation_evidence(evidence) or [e for e in evidence if e['kind']!='documentation' and e['source'].strip()]
    result = reason('Generate exactly five questions from implementation: 2 conceptual, 2 implementation, 1 debugging. Use IDs q1 to q5. Cite exact evidence ID, related_file and related_function. Include concepts and rubric. Do not assume features from README.',compact(eligible),Questions)['questions']
    by_id = {e['evidence_id']:e for e in eligible}
    if Counter(q['category'] for q in result)!=Counter(conceptual=2,implementation=2,debugging=1) or len({q['question_id'] for q in result})!=5:
        raise AppError('Invalid viva question distribution',502,'INVALID_QUESTIONS')
    for q in result:
        source = by_id.get(q['evidence_reference'])
        if not source or q['related_file']!=source['file'] or q['related_function']!=source['symbol'] or q['parent_question_id']:
            raise AppError('Viva citation could not be validated',502,'INVALID_QUESTIONS')
    return result
