from services.evidence_service import build
from tools.dependency_tool import trace
from security.repository_validation import validate_action

def inspect(files,sha):
    return build(files,sha)

def act(root,files,sha,action):
    validate_action(root,action,files)
    selected = {p:files[p] for p in action['files']}
    if action['tool']=='inspect_files':
        evidence,edges = build(selected,sha)
        return evidence,edges,{'inspected_files':list(selected)}
    evidence,edges = build(files,sha)
    if action['tool']=='trace_calls':
        selected_edges = trace(edges,evidence,action['symbol'])
        ids = {e['source'] for e in selected_edges}|{e['target'] for e in selected_edges}
        evidence = [e for e in evidence if e['evidence_id'] in ids or action['symbol'] in e['symbol']]
        return evidence,selected_edges,{'symbol':action['symbol'],'relationships':selected_edges,
            'limitations':['Static resolution does not resolve all instance attributes, dynamic dispatch or data flow.']}
    links = [e for e in edges if e['relation']=='TEST_IMPORTS' and (not selected or e['target'] in selected or e['source'] in selected)]
    paths = {e['source'] for e in links}|{e['target'] for e in links}
    return [e for e in evidence if e['file'] in paths],links,{'test_relationships':links}
