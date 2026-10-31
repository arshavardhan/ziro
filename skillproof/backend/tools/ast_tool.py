"""Static source inspection only; never imports candidate modules."""
import ast
import hashlib
from pathlib import PurePosixPath
from radon.complexity import cc_visit
from schemas.evidence import Evidence

def evidence_id(sha, file, symbol, line):
    return 'ev-' + hashlib.sha256(f'{sha}:{file}:{symbol}:{line}'.encode()).hexdigest()[:20]

def implementation_state(node):
    body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
    def stub(n):
        return (isinstance(n, ast.Pass) or isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and n.value.value is Ellipsis
                or isinstance(n, ast.Raise) and 'NotImplementedError' in ast.unparse(n))
    if not body or all(stub(n) for n in body):
        return 'PLANNED'
    if any(stub(n) for n in ast.walk(node)):
        return 'PARTIALLY_IMPLEMENTED'
    doc = (ast.get_docstring(node) or '').lower()
    if any(word in doc for word in ('placeholder','not implemented','future versions will')):
        return 'PARTIALLY_IMPLEMENTED'
    return 'IMPLEMENTED'

def analyze(files, sha):
    findings = []
    for name, source in files.items():
        if not name.endswith('.py'):
            if name.lower().endswith('.md'):
                findings.append(Evidence(evidence_id=evidence_id(sha,name,'documentation',1), commit_sha=sha, file=name,
                    line_start=1, line_end=max(1,len(source.splitlines())), symbol='documentation', kind='documentation',
                    state='UNVERIFIED', source=source[:8000], limitations=['Documentation is not implementation evidence.']).model_dump(mode='json'))
            elif PurePosixPath(name).suffix.lower() in {'.js','.jsx','.ts','.tsx','.java','.go','.rs','.cs','.cpp','.c','.rb','.php','.swift','.kt'}:
                findings.append(Evidence(evidence_id=evidence_id(sha,name,'module',1),commit_sha=sha,file=name,line_start=1,
                    line_end=max(1,len(source.splitlines())),symbol='module',kind='module',state='UNVERIFIED',source=source[:10000],
                    observed_facts=['Source file inspected as text; language-specific syntax and runtime were not validated.'],
                    limitations=['Python AST/Radon does not validate this language. Model review is interpretive, not verified execution.']).model_dump(mode='json'))
            continue
        lines = source.splitlines()
        try:
            tree = ast.parse(source)
            complexities = {b.lineno:b.complexity for b in cc_visit(source)}
        except (SyntaxError, ValueError, RecursionError):
            findings.append(Evidence(evidence_id=evidence_id(sha,name,'module',1), commit_sha=sha, file=name,
                line_start=1,line_end=max(1,len(lines)),symbol='module',kind='module',state='UNVERIFIED',source=source[:2000],
                limitations=['Python source could not be parsed.']).model_dump(mode='json'))
            continue
        imports = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        def visit(body, prefix=''):
            for node in body:
                if not isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                    continue
                symbol = prefix + node.name
                is_class = isinstance(node,ast.ClassDef)
                kind = 'class' if is_class else ('method' if prefix else 'function')
                state = implementation_state(node)
                if is_class:
                    methods = [n for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
                    if methods and all(implementation_state(n) == 'PLANNED' for n in methods):
                        state = 'PLANNED'
                hints = [ast.unparse(n.annotation) for n in ast.walk(node) if isinstance(n,ast.arg) and n.annotation]
                if getattr(node,'returns',None):
                    hints.append(ast.unparse(node.returns))
                findings.append(Evidence(evidence_id=evidence_id(sha,name,symbol,node.lineno), commit_sha=sha,file=name,
                    line_start=node.lineno,line_end=node.end_lineno,symbol=symbol,kind=kind,state=state,
                    signature=ast.unparse(node.args) if not is_class else ', '.join(ast.unparse(b) for b in node.bases),
                    type_hints=hints,docstring=ast.get_docstring(node),
                    calls=sorted({ast.unparse(n.func) for n in ast.walk(node) if isinstance(n,ast.Call)}),
                    imports=imports,exceptions=[ast.unparse(n.type) if n.type else 'bare except' for n in ast.walk(node) if isinstance(n,ast.ExceptHandler)],
                    complexity=complexities.get(node.lineno),source='\n'.join(lines[node.lineno-1:node.end_lineno])[:10000],
                    observed_facts=[f'{kind} {symbol} at {name}:{node.lineno}-{node.end_lineno}'],
                    limitations=['Static inspection does not establish runtime correctness or candidate authorship.']).model_dump(mode='json'))
                if is_class:
                    visit(node.body,symbol+'.')
        visit(tree.body)
        if not any(e['file'] == name for e in findings):
            findings.append(Evidence(evidence_id=evidence_id(sha,name,'module',1),commit_sha=sha,file=name,line_start=1,
                line_end=max(1,len(lines)),symbol='module',kind='module',state='UNVERIFIED',imports=imports,source=source[:4000],
                limitations=['No function or class implementation found.']).model_dump(mode='json'))
    return findings

def is_test(file):
    path = PurePosixPath(file)
    return 'tests' in path.parts or path.name.startswith('test_') or path.name.endswith('_test.py')
