from core.enums import Status as S
from core.exceptions import AppError

TRANSITIONS = {
    S.QUEUED:{S.PLANNING}, S.PLANNING:{S.ANALYSING}, S.ANALYSING:{S.TESTING},
    S.TESTING:{S.EVALUATING}, S.EVALUATING:{S.VIVA_PENDING},
    S.VIVA_PENDING:{S.APPROVAL_PENDING, S.REJECTED},
    S.APPROVAL_PENDING:{S.APPROVED, S.REJECTED}, S.APPROVED:{S.ISSUED, S.REJECTED},
    S.REJECTED:set(), S.ISSUED:set(), S.FAILED:set(),
}
IN_FLIGHT = {S.QUEUED, S.PLANNING, S.ANALYSING, S.TESTING, S.EVALUATING}

def transition(data, target):
    current = S(data['current_status'])
    target = S(target)
    if current == target:
        return
    if target not in TRANSITIONS[current] and not (target == S.FAILED and current in IN_FLIGHT):
        raise AppError(f'Cannot transition from {current} to {target}')
    data['current_status'] = target.value
