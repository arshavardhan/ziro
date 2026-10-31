from typing import Any, Dict, List, Tuple


def calculate_metrics(
    y_true: List[int],
    y_pred: List[int],
    tool_successes: int,
    tool_totals: int,
    test_exec_successes: int,
    test_exec_totals: int,
    guardrail_successes: int,
    guardrail_totals: int,
    signatures_verified: int,
    signatures_tested: int,
) -> Dict[str, Any]:
    """Compute enterprise-grade evaluation benchmark metrics across 16 test vectors."""
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    total = len(y_true)
    accuracy = (tp + tn) / total if total > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    tool_rate = (tool_successes / tool_totals) if tool_totals > 0 else 1.0
    test_exec_rate = (
        (test_exec_successes / test_exec_totals) if test_exec_totals > 0 else 1.0
    )
    guardrail_rate = (
        (guardrail_successes / guardrail_totals) if guardrail_totals > 0 else 1.0
    )
    sig_rate = (
        (signatures_verified / signatures_tested) if signatures_tested > 0 else 1.0
    )

    return {
        "total_test_cases": total,
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tool_success_rate": round(tool_rate, 4),
        "test_execution_success": round(test_exec_rate, 4),
        "guardrail_success": round(guardrail_rate, 4),
        "credential_verification_rate": round(sig_rate, 4),
        "confusion_matrix": {
            "matrix": [[tn, fp], [fn, tp]],
            "labels": ["Negative / Reject", "Positive / Approve"],
        },
    }
