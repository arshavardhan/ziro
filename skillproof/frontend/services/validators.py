"""SkillProof AI — Validation Services.

Provides input validation for GitHub repository URLs and Candidate IDs
to ensure robust error handling before preparing verification pipelines.
"""
import re
from typing import Tuple
from urllib.parse import urlparse

# Reserved top-level GitHub routes
RESERVED_GITHUB_NAMES = {
    "login",
    "join",
    "explore",
    "trending",
    "pricing",
    "features",
    "settings",
    "notifications",
    "about",
    "contact",
    "security",
    "site",
    "blog",
    "orgs",
    "organizations",
}


def validate_github_url(url: str) -> Tuple[bool, str]:
    """Validate that the entered string is a valid public HTTPS GitHub repository URL.

    Accepts format: https://github.com/username/repository (optional trailing slash).
    Rejects: empty URLs, HTTP URLs, non-GitHub domains, deceptive domains,
             missing usernames, missing repository names, invalid format.

    Args:
        url: The candidate-provided repository URL.

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not url or not url.strip():
        return False, "GitHub repository URL cannot be empty."

    cleaned = url.strip()

    # Reject plain HTTP
    if cleaned.startswith("http://"):
        return False, "Insecure HTTP URLs are not permitted. Please provide a secure 'https://' GitHub URL."

    # Must start with https://
    if not cleaned.startswith("https://"):
        return False, "Invalid URL scheme. URL must start with 'https://'."

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return False, "Invalid URL format. Please provide a well-formed web address."

    if parsed.scheme.lower() != "https":
        return False, "Only HTTPS URLs are supported."

    # Validate exact hostname
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("github.com", "www.github.com"):
        domain = hostname or parsed.netloc or "unknown"
        return False, f"Unsupported URL domain '{domain}'. Only official GitHub ('github.com') repositories are supported."

    # Parse path segments
    raw_path = parsed.path.strip("/")
    if not raw_path:
        return False, "Missing repository username and repository name."

    path_parts = [p for p in raw_path.split("/") if p]
    if len(path_parts) == 0:
        return False, "Missing repository username and repository name."
    elif len(path_parts) == 1:
        return False, "Missing repository name in GitHub URL."
    elif len(path_parts) > 2:
        return False, "Invalid GitHub repository URL. Please provide a repository root URL: 'https://github.com/username/repository'."

    owner, repo = path_parts[0], path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not owner.strip():
        return False, "Missing repository username."
    if not repo or not repo.strip() or repo == ".git":
        return False, "Missing repository name."

    # Character validity
    if not re.match(r"^[A-Za-z0-9_.-]+$", owner) or not re.match(r"^[A-Za-z0-9_.-]+$", repo):
        return False, "Invalid characters in GitHub repository username or repository name."

    if owner.lower() in RESERVED_GITHUB_NAMES:
        return False, f"'{owner}' is a reserved GitHub keyword, not a valid repository username."

    return True, ""


def extract_github_repo_info(url: str) -> Tuple[str, str]:
    """Extract (owner, repo_name) from a validated GitHub repository URL.

    Args:
        url: Validated GitHub repository URL.

    Returns:
        Tuple[str, str]: (owner, repo_name)
    """
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) >= 2:
        owner = path_parts[0]
        repo = path_parts[1].replace(".git", "")
        return owner, repo
    return "", ""


def validate_candidate_id(cand_id: str) -> Tuple[bool, str]:
    """Validate that Candidate ID is present, non-empty, and conforms to basic ID format.

    Args:
        cand_id: The candidate ID string.

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not cand_id or not cand_id.strip():
        return False, "Candidate ID cannot be empty. Please enter a valid candidate identifier."

    cleaned = cand_id.strip()
    if len(cleaned) < 2:
        return False, "Candidate ID must be at least 2 characters long."

    return True, ""
