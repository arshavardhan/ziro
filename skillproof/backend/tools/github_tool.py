import os
import subprocess
import time
import json
from datetime import datetime,timezone
from pathlib import Path
import httpx
import config
from core.guardrails import validate_url, safe_file, redact
from core.exceptions import AppError

def git(root, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args],
                          env=env, capture_output=True, text=True, timeout=30, check=True).stdout

def clone(url, session_id, commit_sha=None):
    url=validate_url(url)
    owner_repo = url.removeprefix('https://github.com/')
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
        try:
            response = client.get('https://api.github.com/repos/' + owner_repo)
        except httpx.HTTPError as exc:
            raise AppError('GitHub metadata network request failed',502,'REPOSITORY_NETWORK_ERROR') from exc
        if response.status_code != 200:
            raise AppError('Public repository missing, private, or GitHub rate limit reached',422,'REPOSITORY_UNAVAILABLE')
        info = response.json()
        if info.get('private') or info.get('size', 0) * 1024 > config.MAX_CLONE_BYTES:
            raise AppError('Repository is private or exceeds the configured clone limit',422,'REPOSITORY_REJECTED')
    root = config.WORKSPACES / session_id
    if root.parent.resolve()!=config.WORKSPACES.resolve():
        raise AppError('Invalid assessment workspace',422,'INVALID_WORKSPACE')
    root.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_LFS_SKIP_SMUDGE='1')
    command = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'protocol.file.allow=never',
               '-c', 'http.followRedirects=false', 'clone', '--no-checkout', '--depth', '100', '--', url, str(root)]
    with subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as process:
        start = time.monotonic()
        while process.poll() is None:
            size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) if root.exists() else 0
            if time.monotonic() - start > 120 or size > config.MAX_CLONE_BYTES:
                process.kill()
                process.wait()
                raise AppError('Clone exceeded time or size limit',422,'CLONE_LIMIT')
            time.sleep(.1)
        if process.returncode:
            raise AppError('Public repository clone failed',502,'CLONE_FAILED')
    # Sidecar is outside the exported source tree and never treated as candidate evidence.
    (root.parent/(root.name+'.acquisition.json')).write_text(json.dumps({'owner':info.get('owner',{}).get('login'),'name':info.get('name'),
        'default_branch':info.get('default_branch'),'cloned_at':datetime.now(timezone.utc).isoformat()}),encoding='utf-8')
    try:
        git(root,'rev-parse','--verify','HEAD')
    except subprocess.CalledProcessError as exc:
        raise AppError('Repository has no commit to analyze',422,'EMPTY_REPOSITORY') from exc
    # Export blobs ourselves: no checkout filters, symlinks, submodules, or hooks.
    if commit_sha:
        import re
        if not re.fullmatch('[0-9a-fA-F]{40}', commit_sha):
            raise ValueError('Invalid commit SHA')
        try:
            git(root, 'cat-file', '-e', commit_sha + '^{commit}')
        except subprocess.CalledProcessError as exc:
            raise ValueError('Requested commit is outside the fetched 100-commit history') from exc
        git(root, 'update-ref', 'HEAD', commit_sha)
    entries = git(root, 'ls-tree', '-rl', 'HEAD').splitlines()
    total = 0
    for entry in entries:
        metadata, name = entry.split('\t', 1)
        mode, kind, oid, size = metadata.split()
        if kind != 'blob' or mode not in {'100644', '100755'}:
            continue
        total += int(size)
        if total > config.MAX_REPO_BYTES:
            raise ValueError('Expanded repository exceeds size limit')
        if int(size) > config.MAX_FILE_BYTES:
            continue
        try:
            path = safe_file(root, name)
        except ValueError:
            continue
        blob = subprocess.run(['git', '-C', str(root), 'cat-file', 'blob', oid], capture_output=True, timeout=10, check=True).stdout
        if b'\0' in blob:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    return root

def inspect(root):
    files = {}
    for path in sorted(Path(root).rglob('*')):
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        try:
            safe_file(root, name)
            if path.stat().st_size > config.MAX_FILE_BYTES:
                continue
            content = path.read_text(encoding='utf-8')
            if '\0' not in content:
                files[name] = redact(content)
        except (ValueError, UnicodeError, OSError):
            continue
        if len(files) >= config.MAX_FILES:
            break
    languages = sorted({{'.py':'Python', '.js':'JavaScript', '.ts':'TypeScript', '.java':'Java', '.go':'Go'}.get(Path(p).suffix, 'Other') for p in files})
    return files, languages

