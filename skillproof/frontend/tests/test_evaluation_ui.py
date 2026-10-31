import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.run_evaluation import run_benchmark, load_test_cases


def test_16_cases_evaluation():
    """Verify evaluation benchmark executes all 16 test cases successfully."""
    cases = load_test_cases()
    assert len(cases) == 16

    out = run_benchmark()
    m = out["metrics"]
    assert m["total_test_cases"] == 16
    assert m["accuracy"] == 1.0
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0
    assert m["credential_verification_rate"] == 1.0
    assert len(out["results"]) == 16
