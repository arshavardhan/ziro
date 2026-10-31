import ast
import pytest
from core.guardrails import safe_file,validate_url,redact
from security.sandbox import docker_command
from security.repository_validation import validate_action

@pytest.mark.parametrize('url',['http://github.com/a/b','https://evil.com/a/b','https://github.com/a/../b','https://github.com/a/b?x=1','https://user:pass@github.com/a/b'])
def test_url_guard(url):
    with pytest.raises(ValueError):
        validate_url(url)

@pytest.mark.parametrize('name',['../outside.py','.env','.env.production','.git/config','private.key','secrets.txt'])
def test_path_guard(tmp_path,name):
    with pytest.raises(ValueError):
        safe_file(tmp_path,name)

def test_redaction_preserves_python():
    source='def f(api_key: str):\n    token = "sensitive"\n    return api_key\n'
    sanitized=redact(source)
    ast.parse(sanitized)
    assert 'sensitive' not in sanitized

def test_sandbox_limits(tmp_path):
    command=docker_command(tmp_path,'test')
    for required in ['--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--memory=512m']:
        assert required in command
    assert not any('API_KEY' in value for value in command)

def test_llm_cannot_select_shell(tmp_path):
    with pytest.raises(Exception):
        validate_action(tmp_path,{'tool':'shell','files':[]},[])
