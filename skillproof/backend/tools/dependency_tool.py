import ast
from pathlib import PurePosixPath

def module_name(path):
    return path.removesuffix('.py').replace('/','.').removesuffix('.__init__')

def relationships(files, evidence):
    edges = []
    modules = {module_name(p):p for p in files if p.endswith('.py')}
    symbols = {module_name(e['file'])+'.'+e['symbol']:e for e in evidence if e['kind'] in {'function','method','class'}}
    for file,source in files.items():
        if not file.endswith('.py'):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        aliases = {}
        package = module_name(file).split('.') if file.endswith('__init__.py') else module_name(file).split('.')[:-1]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                for alias in node.names:
                    aliases[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
            elif isinstance(node,ast.ImportFrom):
                prefix = '.'.join(package[:len(package)-node.level+1]) if node.level else ''
                base = '.'.join(x for x in [prefix,node.module] if x)
                for alias in node.names:
                    aliases[alias.asname or alias.name] = base+'.'+alias.name
                if base in modules:
                    edges.append(dict(source=file,target=modules[base],relation='IMPORTS',file=file,line=node.lineno,resolution='static'))
        instances={}
        for cls in [n for n in tree.body if isinstance(n,ast.ClassDef)]:
            for assignment in [n for n in ast.walk(cls) if isinstance(n,ast.Assign)]:
                for target in assignment.targets:
                    if isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name) and target.value.id=='self':
                        constructors=[ast.unparse(n.func) for n in ast.walk(assignment.value) if isinstance(n,ast.Call)]
                        for constructor in constructors:
                            full=aliases.get(constructor,constructor)
                            if full in symbols and symbols[full]['kind']=='class':
                                instances[(cls.name,target.attr)]=full
        def resolve(call,item):
            head,*tail=call.split('.')
            full='.'.join([aliases.get(head,head),*tail])
            candidates=[full,module_name(file)+'.'+full]
            if head=='self' and '.' in item['symbol']:
                cls=item['symbol'].split('.')[0]
                candidates.append(module_name(file)+'.'+cls+'.'+'.'.join(tail))
                if len(tail)>=2 and (cls,tail[0]) in instances:
                    candidates.append(instances[(cls,tail[0])]+'.'+'.'.join(tail[1:]))
            return next((symbols[c] for c in candidates if c in symbols),None)
        for item in [e for e in evidence if e['file'] == file and e['kind'] in {'function','method'}]:
            for call in item['calls']:
                head,*tail = call.split('.')
                full = '.'.join([aliases.get(head,head),*tail])
                candidates = [full,module_name(file)+'.'+full]
                if head == 'self' and '.' in item['symbol']:
                    candidates.append(module_name(file)+'.'+item['symbol'].rsplit('.',1)[0]+'.'+'.'.join(tail))
                target = resolve(call,item)
                if target:
                    edges.append(dict(source=item['evidence_id'],target=target['evidence_id'],relation='CALLS',file=file,line=item['line_start'],resolution='static_name_resolution'))
            node=next((n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.lineno==item['line_start']),None)
            origins={}
            if node:
                for assignment in sorted([n for n in ast.walk(node) if isinstance(n,(ast.Assign,ast.AnnAssign))],key=lambda n:n.lineno):
                    if assignment.value is None:
                        continue
                    refs=set()
                    for part in ast.walk(assignment.value):
                        if isinstance(part,ast.Call):
                            target=resolve(ast.unparse(part.func),item)
                            if target:
                                refs.add(target['evidence_id'])
                        elif isinstance(part,ast.Name):
                            refs.update(origins.get(part.id,set()))
                    targets=assignment.targets if isinstance(assignment,ast.Assign) else [assignment.target]
                    for target in targets:
                        if isinstance(target,ast.Name):
                            origins[target.id]=refs
                for call in [n for n in ast.walk(node) if isinstance(n,ast.Call)]:
                    target=resolve(ast.unparse(call.func),item)
                    if target:
                        for keyword in call.keywords:
                            refs=set().union(*(origins.get(n.id,set()) for n in ast.walk(keyword.value) if isinstance(n,ast.Name)))
                            for ref in refs:
                                if ref!=target['evidence_id']:
                                    edges.append(dict(source=ref,target=target['evidence_id'],relation='PASSES_VALUE:'+str(keyword.arg),file=file,line=call.lineno,resolution='static_assignment_heuristic'))
        # Import relationships support module-level test links, not proof that every function ran.
        from tools.ast_tool import is_test
        if is_test(file):
            for target in set(aliases.values()):
                module = target if target in modules else target.rsplit('.',1)[0]
                if module in modules:
                    edges.append(dict(source=file,target=modules[module],relation='TEST_IMPORTS',file=file,line=1,resolution='module_level_static'))
    unique = {tuple(e.values()):e for e in edges}
    return list(unique.values())

def trace(edges, evidence, symbol):
    ids = {e['evidence_id'] for e in evidence if symbol in e['symbol']}
    return [edge for edge in edges if edge['source'] in ids or edge['target'] in ids]
