from services.repository_service import snapshot,inspect_snapshot

def run(url,session_id,commit_sha=None):
    return snapshot(url,session_id,commit_sha)

def resume(root,url,sha):
    result = inspect_snapshot(root,url)
    if result[2]['commit_sha']!=sha:
        raise ValueError('Workspace commit changed; cannot resume pinned analysis')
    return result
