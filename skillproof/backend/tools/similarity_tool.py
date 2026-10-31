import ast
import hashlib
import io
import tokenize
from difflib import SequenceMatcher
from itertools import combinations

def indicators(files):
    functions = []
    for file,source in files.items():
        if not file.endswith('.py'):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                dump = ast.dump(ast.Module(body=node.body,type_ignores=[]),include_attributes=False)
                if len(dump) < 180:
                    continue
                text = ast.get_source_segment(source,node) or ''
                tokens = [t.string for t in tokenize.generate_tokens(io.StringIO(text).readline) if t.type not in {tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT}]
                functions.append((file,node.lineno,dump,tokens[:1000]))
    findings = []
    for left,right in combinations(functions[:200],2):
        exact = left[2] == right[2]
        similarity = 1.0 if exact else SequenceMatcher(None,left[3],right[3],autojunk=False).ratio()
        if similarity < .9:
            continue
        findings.append(dict(finding_id='sim-'+hashlib.sha256(f'{left[:2]}:{right[:2]}'.encode()).hexdigest()[:16],
            files=[left[0],right[0]],lines=[left[1],right[1]],similarity=round(similarity,3),
            measure='AST body fingerprint' if exact else 'token sequence similarity',
            evidence=f'{left[0]}:{left[1]} resembles {right[0]}:{right[1]}', severity='medium' if exact else 'low',
            explanation='Similar internal implementation patterns; inspect context and common boilerplate.',
            limitations=['Within-repository comparison only; no internet-wide search or plagiarism conclusion.', 'Comparison limited to first 200 substantial functions.']))
        if len(findings) >= 100:
            break
    return findings
