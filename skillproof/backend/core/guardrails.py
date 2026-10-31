import re
from pathlib import Path

def validate_url(value):
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100})/?', value)
    if not match or match[2] in ('.', '..', '.git'):
        raise ValueError('Use a public HTTPS GitHub repository URL: https://github.com/owner/repo')
    return value.rstrip('/').removesuffix('.git')

def safe_file(root, name):
    if ':' in name or '\x00' in name:
        raise ValueError('Unsafe repository path')
    root = Path(root).resolve()
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('Unsafe repository path')
    if any(p.lower() in {'.git', '.env', '.aws', '.ssh', 'node_modules', '.venv'} for p in path.relative_to(root).parts):
        raise ValueError('Excluded path')
    if path.name.lower().startswith('.env') or any(word in path.name.lower() for word in ('secret', 'credential', 'id_rsa')) or path.suffix in {'.pem', '.key'}:
        raise ValueError('Sensitive file excluded')
    return path

def redact(text):
    # Preserve Python syntax/type annotations; redact literal values, not variable references.
    text = re.sub(r'''(?i)((?:["']?)(?:api[_-]?key|password|token|secret)(?:["']?)\s*[:=]\s*)(["'])([^"'\n]+)\2''', r'\1\2[REDACTED]\2', text)
    text = re.sub(r'(?m)^((?:API_KEY|LLM_API_KEY|PASSWORD|TOKEN|SECRET)=)[^\r\n]+',r'\1[REDACTED]',text)
    return re.sub(r'\b(?:sk-[\w-]{12,}|gh[pousr]_[\w]{16,})\b', '[REDACTED]', text)
