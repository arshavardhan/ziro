import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.run_evaluation import run_benchmark, load_test_cases


def test_test_cases_integrity():
    """Verify test cases count and schema."""
    cases = load_test_cases()
    assert len(cases) >= 15
    for c in cases:
        assert "id" in c
        assert "name" in c
        assert "expected_outcome" in c
        assert "ground_truth" in c["expected_outcome"]


def test_benchmark_metrics():
    """Verify benchmark run achieves 100% decision convergence."""
    out = run_benchmark()
    m = out["metrics"]
    assert m["total_test_cases"] >= 15
    assert m["accuracy"] == 1.0
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0
    assert m["credential_verification_rate"] == 1.0
