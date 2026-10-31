from agents.llm import reason
from schemas.agents import Plan

def plan(request):
    return reason('PLAN: use the supplied real repository baseline and inventory to choose investigation actions for claimed skills. Select only actual paths. Give a concise decision summary, never private chain-of-thought or shell commands. Investigate relationships or missing tests that would change the assessment.',request,Plan)

def critique(observations):
    return reason('CRITIQUE and RE-PLAN: identify gaps and select inspect_files, trace_calls or find_tests using inventory paths. Trace caller/consumer relationships rather than assuming integration. Continue with concrete actions if gaps can be investigated, otherwise stop=true. Maximum three cycles including initial investigation.',observations,Plan)
