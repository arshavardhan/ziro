from tools.ast_tool import analyze, is_test
from tools.dependency_tool import relationships

def build(files,sha):
    evidence = analyze(files,sha)
    edges = relationships(files,evidence)
    for item in evidence:
        item['test_references'] = sorted({edge['source'] for edge in edges if edge['relation']=='TEST_IMPORTS' and edge['target']==item['file']})
    for item in evidence:
        edges.append(dict(source=item['file'],target=item['evidence_id'],relation='CONTAINS',file=item['file'],line=item['line_start'],resolution='AST'))
    return evidence,edges

def implementation_evidence(items):
    return [e for e in items if e['kind'] in {'function','method','class'} and e['state'] in {'IMPLEMENTED','TESTED','PARTIALLY_IMPLEMENTED'} and not is_test(e['file'])]

def attach_results(evidence, result):
    # A module import relationship does not prove execution of a particular function.
    for item in evidence:
        if item['test_references']:
            item['observed_facts'].append('Related test files statically import this module: '+', '.join(item['test_references']))
            item['limitations'].append('Test-to-module relation is static; function coverage is not established.')
