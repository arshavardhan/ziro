from services.credential_service import issue

def run(session_id):
    """Only delegates to deterministic approval and signing gates; no LLM can bypass them."""
    return issue(session_id)
