from core.guardrails import safe_file,validate_url
from core.exceptions import AppError

def validate_action(root,action,inventory):
    if action['tool'] not in {'inspect_files','trace_calls','find_tests'}:
        raise AppError('Unsupported analysis tool',422,'INVALID_TOOL')
    for name in action['files']:
        safe_file(root,name)
        if name not in inventory:
            raise AppError('Planner selected a file outside the repository inventory',502,'INVALID_TOOL_ARGUMENT')
    if action['tool']=='trace_calls' and not action.get('symbol'):
        raise AppError('Call trace requires a symbol',502,'INVALID_TOOL_ARGUMENT')
