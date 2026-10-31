import tomllib
import json
import hashlib
from datetime import datetime, timezone
from tools.github_tool import clone, inspect, git

def snapshot(url, session_id, commit_sha=None):
    root = clone(url, session_id, commit_sha)
    return inspect_snapshot(root,url)

def inspect_snapshot(root,url):
    files,languages = inspect(root)
    sha = git(root,'rev-parse','HEAD').strip()
    dependencies, entries = [],[]
    if 'pyproject.toml' in files:
        try:
            project = tomllib.loads(files['pyproject.toml']).get('project',{})
            dependencies = project.get('dependencies',[])
            entries = list(project.get('scripts',{}).values())
        except tomllib.TOMLDecodeError:
            pass
    for file,source in files.items():
        if file.endswith('requirements.txt'):
            dependencies.extend(line.strip() for line in source.splitlines() if line.strip() and not line.startswith('#'))
        if file.endswith('__main__.py') or "if __name__ ==" in source and file.endswith('.py'):
            entries.append(file)
    context = {p:s[:8000] for p,s in files.items() if p.lower().endswith(('readme.md','pyproject.toml','requirements.txt','roadmap.md')) or p.startswith('.github/workflows/')}
    info = dict(repository_url=url,commit_sha=sha,captured_at=datetime.now(timezone.utc).isoformat(),languages=languages,
        files=list(files),directory_tree=list(files),dependencies=dependencies,entry_points=entries,
        ci_workflows=[p for p in files if p.startswith('.github/workflows/')],context=context,
        limitations=['Inventory capped at 500 text files; files over 100 KB, binary, secret and symlink files excluded.'])
    sidecar=root.parent/(root.name+'.acquisition.json')
    if sidecar.exists():
        info.update(json.loads(sidecar.read_text(encoding='utf-8')))
    else:
        info.update(owner=url.rstrip('/').split('/')[-2],name=url.rstrip('/').split('/')[-1],default_branch=None,cloned_at=None)
    info['file_hashes']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
    return root,files,info
