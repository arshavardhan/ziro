import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.api_client import APIClient


def test_api_client_initialization():
    """Verify API client configuration and URL trimming."""
    client = APIClient(base_url="http://192.168.1.100:8000/", timeout=8)
    assert client.base_url == "http://192.168.1.100:8000"
    assert client.timeout == 8


def test_api_client_unreachable_backend_handling():
    """Verify client handles offline backend gracefully without crashing."""
    client = APIClient(base_url="http://127.0.0.1:9998", timeout=1)
    healthy, msg = client.check_health()
    assert healthy is False
    assert "Cannot connect" in msg or "Ensure Laptop 1 is running" in msg

    ok, data, err = client.start_analysis("CAND-001", "https://github.com/arshavardhan/AegisAi", ["Python"])
    assert ok is False
    assert len(err) > 0


def test_api_client_verify_credential_fallback():
    """Verify client endpoint handles verification error responses gracefully."""
    client = APIClient(base_url="http://127.0.0.1:9998", timeout=1)
    is_valid, data, err = client.verify_credential("SP-CRED-TEST")
    assert is_valid is False
