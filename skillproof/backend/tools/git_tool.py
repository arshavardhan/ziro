from tools.github_tool import git
from core.guardrails import redact

def history(root, sha):
    log = git(root,'log','-100','--format=%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s','--numstat',sha)
    commits, introduced = [], {}
    for block in log.split('\x1e'):
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        parts = lines[0].split('\x1f',4)
        if len(parts) != 5:
            continue
        commit_sha,author,email,timestamp,message = parts
        changed,added,deleted = [],0,0
        for line in lines[1:]:
            if '\t' not in line:
                continue
            plus,minus,file = line.split('\t',2)
            changed.append(file)
            added += int(plus) if plus.isdigit() else 0
            deleted += int(minus) if minus.isdigit() else 0
            introduced[file] = commit_sha
        commits.append(dict(sha=commit_sha,author_name=redact(author),author_email=redact(email),timestamp=timestamp,message=redact(message),
            changed_files=changed,additions=added,deletions=deleted,
            test_modifications=[p for p in changed if 'test' in p],documentation_modifications=[p for p in changed if p.endswith('.md')]))
    anomalies = []
    if any(c['additions'] > 1000 for c in commits):
        anomalies.append('Large code introduction (>1000 added lines) observed; not evidence of copied or AI-generated authorship.')
    if len(commits)>1 and len({c['message'] for c in commits}) < len(commits)/2:
        anomalies.append('Repetitive commit messages; interpretation requires human review.')
    return dict(commit_count=len(commits),commits=commits,file_introduction=introduced,anomalies=anomalies,
        feature_progression=[f"{c['sha'][:8]}: {c['message']} ({len(c['changed_files'])} changed files)" for c in reversed(commits)],
        limitations=['At most 100 commits. File introduction means earliest observed modification in this history window.',
                      'Author metadata does not prove personal authorship; messages do not independently verify features.'])
