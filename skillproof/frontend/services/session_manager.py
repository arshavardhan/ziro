import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import streamlit as st

SECRET_KEY = "skillproof-enterprise-hmac-key-2026"


def compute_signature(payload: Dict[str, Any], secret: str = SECRET_KEY) -> str:
    """Generate deterministic HMAC-SHA256 signature for verifiable credentials."""
    canonical = json.dumps(payload, sort_keys=True)
    return hmac.new(
        secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_signature(
    payload: Dict[str, Any], signature: str, secret: str = SECRET_KEY
) -> bool:
    """Validate HMAC-SHA256 signature against payload."""
    expected = compute_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


# ==============================================================================
# AEGIS-AI PRIMARY CANDIDATE DETERMINISTIC BENCHMARK FIXTURE
# Target: https://github.com/arshavardhan/AegisAi | Candidate: CAND-001
# ==============================================================================

AEGIS_REPO_INFO = {
    "repo_name": "AegisAi",
    "repo_url": "https://github.com/arshavardhan/AegisAi",
    "commit_sha": "e4b971a8f9c08d234a11b6f0e9e4a8f9d0c2b1e7",
    "default_branch": "main",
    "languages": {"Python": 98.4, "Shell": 1.6},
    "dependencies": [
        "torch>=2.1.0",
        "scikit-learn>=1.3.0",
        "scipy>=1.11.0",
        "numpy>=1.24.0",
        "pydantic>=2.4.0",
        "joblib>=1.3.0",
        "pytest>=7.4.0",
    ],
    "discovered_modules": [
        "aegis/core",
        "aegis/uncertainty",
        "aegis/ood",
        "aegis/drift",
        "aegis/scoring",
        "aegis/recommendation",
        "aegis/wrappers",
        "tests",
    ],
    "ci_config": ".github/workflows/ci.yml (pytest & black passing)",
    "readme_summary": "Production-grade AI safety and reliability framework for uncertainty estimation, out-of-distribution (OOD) detection, and input drift monitoring.",
}

AEGIS_CODE_FILES = {
    "aegis/core/base.py": '''"""Core abstractions and BaseDetector class for AegisAI framework."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np

class BaseDetector(ABC):
    """Abstract Base Class for all model governance and OOD detectors."""
    
    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        self._is_fitted = False

    @abstractmethod
    def fit(self, X_train: np.ndarray, y_train: Optional[np.ndarray] = None) -> "BaseDetector":
        """Calibrate detector parameters on in-distribution training data."""
        pass

    @abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray:
        """Compute continuous anomaly or uncertainty scores for incoming queries."""
        pass

    def evaluate_safety(self, X: np.ndarray) -> Dict[str, Any]:
        """Generate binary safety verdict and calibrated risk metrics."""
        scores = self.score(X)
        is_safe = scores < self.confidence_threshold
        return {
            "is_safe": bool(np.all(is_safe)),
            "mean_risk_score": float(np.mean(scores)),
            "flagged_samples_count": int(np.sum(~is_safe))
        }
''',
    "aegis/uncertainty/monte_carlo.py": '''"""Epistemic Uncertainty Estimation via Monte Carlo Dropout Sampling."""
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple

class MCDropoutEstimator:
    """Estimates model uncertainty by performing stochastic forward passes with active dropout."""
    
    def __init__(self, model: nn.Module, num_samples: int = 30):
        self.model = model
        self.num_samples = num_samples

    def estimate_uncertainty(self, x: torch.Tensor) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Execute N forward passes in train mode to sample predictive posterior distribution."""
        self.model.train()  # Retain dropout active at test inference
        predictions = []

        with torch.no_grad():
            for _ in range(self.num_samples):
                logits = self.model(x)
                probs = torch.softmax(logits, dim=-1)
                predictions.append(probs.cpu().numpy())

        preds_array = np.stack(predictions, axis=0) # [samples, batch, classes]
        mean_preds = np.mean(preds_array, axis=0)
        variance = np.var(preds_array, axis=0)
        
        # Predictive Entropy computation: -sum(p * log(p))
        entropy = -np.sum(mean_preds * np.log(mean_preds + 1e-12), axis=-1)
        return mean_preds, variance, entropy
''',
    "aegis/ood/mahalanobis.py": '''"""Out-of-Distribution Detection via Class-Conditional Mahalanobis Distance."""
import numpy as np
from scipy.spatial.distance import cdist
from typing import Dict, List

class MahalanobisOODDetector:
    """Calculates class-conditional Mahalanobis distances in deep latent feature space."""
    
    def __init__(self, num_classes: int):
        self.num_classes = num_classes
        self.class_means: Dict[int, np.ndarray] = {}
        self.shared_precision: Optional[np.ndarray] = None

    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        """Calculate class centroids and pooled empirical covariance precision matrix."""
        cov_sum = np.zeros((features.shape[1], features.shape[1]))
        
        for c in range(self.num_classes):
            class_feats = features[labels == c]
            mean_c = np.mean(class_feats, axis=0)
            self.class_means[c] = mean_c
            diff = class_feats - mean_c
            cov_sum += np.dot(diff.T, diff)

        pooled_cov = cov_sum / len(features)
        # Regularization for numerical stability
        pooled_cov += np.eye(pooled_cov.shape[0]) * 1e-5
        self.shared_precision = np.linalg.pinv(pooled_cov)

    def score(self, query_features: np.ndarray) -> np.ndarray:
        """Return minimum Mahalanobis distance to any training class centroid."""
        min_distances = []
        for x in query_features:
            dists = [
                float(np.sqrt(np.dot(np.dot(x - mean_c, self.shared_precision), (x - mean_c).T)))
                for mean_c in self.class_means.values()
            ]
            min_distances.append(min(dists))
        return np.array(min_distances)
''',
    "aegis/drift/drift_detector.py": '''"""Distributional Data Drift Detection using Kolmogorov-Smirnov & PSI."""
import numpy as np
from scipy import stats
from typing import Dict, Any

class DataDriftMonitor:
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
        self.reference_distribution = {}

    def fit(self, reference_data: np.ndarray) -> None:
        for idx in range(reference_data.shape[1]):
            self.reference_distribution[idx] = reference_data[:, idx]

    def check_drift(self, incoming_data: np.ndarray) -> Dict[str, Any]:
        drifted_features = []
        p_values = {}
        
        for idx in range(incoming_data.shape[1]):
            stat, p_val = stats.ks_2samp(self.reference_distribution[idx], incoming_data[:, idx])
            p_values[f"feature_{idx}"] = round(float(p_val), 5)
            if p_val < self.alpha:
                drifted_features.append(idx)

        return {
            "drift_detected": len(drifted_features) > 0,
            "drifted_count": len(drifted_features),
            "p_values": p_values,
            "severity": "HIGH" if len(drifted_features) > 2 else ("MEDIUM" if drifted_features else "LOW")
        }
''',
    "aegis/scoring/risk_engine.py": '''"""Composite Risk Scoring Engine fusing OOD, Drift, and Predictive Uncertainty."""
import numpy as np
from typing import Dict, Any

class CompositeRiskEngine:
    def __init__(self, w_uncertainty: float = 0.4, w_ood: float = 0.4, w_drift: float = 0.2):
        self.w_uncertainty = w_uncertainty
        self.w_ood = w_ood
        self.w_drift = w_drift

    def compute_composite_risk(self, entropy: np.ndarray, ood_score: np.ndarray, drift_score: float) -> Dict[str, Any]:
        norm_entropy = np.clip(entropy / 2.5, 0.0, 1.0)
        norm_ood = np.clip(ood_score / 10.0, 0.0, 1.0)
        composite = (self.w_uncertainty * norm_entropy) + (self.w_ood * norm_ood) + (self.w_drift * drift_score)
        
        return {
            "composite_risk_score": float(np.mean(composite)),
            "action_recommendation": "REJECT_PREDICTION" if np.mean(composite) > 0.75 else ("HUMAN_REVIEW" if np.mean(composite) > 0.45 else "PASS_AUTOMATIC")
        }
''',
    "tests/test_uncertainty.py": '''"""Automated Pytest Harness for AegisAI Monte Carlo & Drift Modules."""
import pytest
import numpy as np
import torch
import torch.nn as nn
from aegis.uncertainty.monte_carlo import MCDropoutEstimator
from aegis.drift.drift_detector import DataDriftMonitor

def test_mc_dropout_variance():
    model = nn.Sequential(nn.Linear(10, 20), nn.Dropout(0.5), nn.Linear(20, 2))
    estimator = MCDropoutEstimator(model, num_samples=15)
    x = torch.randn(4, 10)
    mean_preds, variance, entropy = estimator.estimate_uncertainty(x)
    assert mean_preds.shape == (4, 2)
    assert np.all(variance >= 0.0)
    assert len(entropy) == 4

def test_drift_detection_clean():
    monitor = DataDriftMonitor()
    ref = np.random.normal(0, 1, (1000, 3))
    monitor.fit(ref)
    clean_sample = np.random.normal(0, 1, (200, 3))
    res = monitor.check_drift(clean_sample)
    assert res["drift_detected"] is False
''',
}

AEGIS_GIT_COMMITS = [
    {
        "hash": "7a1b40c",
        "date": "2026-10-12 11:20:00",
        "author": "Arsha Vardhan <arsha@aegis.dev>",
        "message": "feat(core): initial BaseDetector abstract structure and config schema",
        "files_changed": 3,
        "insertions": 142,
        "deletions": 0,
    },
    {
        "hash": "c3e8912",
        "date": "2026-10-15 14:45:12",
        "author": "Arsha Vardhan <arsha@aegis.dev>",
        "message": "feat(uncertainty): implement MCDropoutEstimator with batch entropy calculations",
        "files_changed": 2,
        "insertions": 98,
        "deletions": 14,
    },
    {
        "hash": "9f201dd",
        "date": "2026-10-18 09:15:33",
        "author": "Arsha Vardhan <arsha@aegis.dev>",
        "message": "feat(ood): class-conditional Mahalanobis distance with covariance regularization",
        "files_changed": 1,
        "insertions": 86,
        "deletions": 5,
    },
    {
        "hash": "5d4e8aa",
        "date": "2026-10-21 16:30:40",
        "author": "Arsha Vardhan <arsha@aegis.dev>",
        "message": "feat(drift): integrate two-sample Kolmogorov-Smirnov test suite for distribution shift",
        "files_changed": 2,
        "insertions": 64,
        "deletions": 8,
    },
    {
        "hash": "e4b971a",
        "date": "2026-10-26 18:00:22",
        "author": "Arsha Vardhan <arsha@aegis.dev>",
        "message": "test(core): add comprehensive pytest suite for MC dropout and drift monitors",
        "files_changed": 1,
        "insertions": 52,
        "deletions": 2,
    },
]

AEGIS_AGENT_TRAJECTORY = [
    {
        "agent": "Master Planner",
        "stage": "PLAN",
        "objective": "Formulate verification plan for AegisAI claimed skills",
        "status": "COMPLETED",
        "tool": "dag_planner",
        "observation": "Target repo AegisAI contains advanced ML guardrail components. Claimed: Python, OOP, ML, Architecture, Testing, Git, API Development.",
        "output": "Generated 7-stage DAG: Repo Intelligence -> AST Code Understanding -> Test Harness Execution -> Git Forensics -> Originality Check -> Skill Assessment -> Viva Synthesis.",
        "timestamp": "10:30:02",
    },
    {
        "agent": "Repository Intelligence",
        "stage": "ACT",
        "objective": "Clone tree, extract package structure, check CI/CD",
        "status": "COMPLETED",
        "tool": "repo_tree_parser",
        "observation": "Discovered 8 active modules: aegis/core, aegis/uncertainty, aegis/ood, aegis/drift, aegis/scoring, aegis/recommendation, aegis/wrappers, tests. Found .github/workflows/ci.yml.",
        "output": "Confirmed clean Python package architecture with setup.py and pyproject.toml.",
        "timestamp": "10:30:15",
    },
    {
        "agent": "Code Understanding",
        "stage": "OBSERVE",
        "objective": "Parse AST, inspect class hierarchies, type annotations, and complexity",
        "status": "COMPLETED",
        "tool": "ast_code_analyzer",
        "observation": "Analyzed BaseDetector (ABC), MCDropoutEstimator, MahalanobisOODDetector. Found robust type hinting, docstrings, and clean modular encapsulation.",
        "output": "Extracted 14 verified classes, 26 methods. Complexity metric: Low/Maintainable (Cyclomatic avg 3.8).",
        "timestamp": "10:30:28",
    },
    {
        "agent": "Test Verification",
        "stage": "CRITIQUE",
        "objective": "Execute pytest suite in sandboxed test runner",
        "status": "REPLANNING",
        "tool": "pytest_runner",
        "observation": "Pytest discovered 18 test cases across tests/. All 18 passed. However, code coverage in aegis/recommendation is 62%, requiring deeper branch exploration.",
        "output": "Triggering RE-PLAN event: Dispatched secondary static analysis to evaluate unreached branches in recommendation engine.",
        "timestamp": "10:30:42",
    },
    {
        "agent": "Code Understanding",
        "stage": "ACT AGAIN",
        "objective": "Inspect secondary recommendation branches and decision boundaries",
        "status": "COMPLETED",
        "tool": "ast_branch_analyzer",
        "observation": "Analyzed CompositeRiskEngine thresholds (0.45 human review, 0.75 rejection). Logic is sound and verified against edge test cases.",
        "output": "Branch verification cleared. Confidence elevated to 94%.",
        "timestamp": "10:30:54",
    },
    {
        "agent": "Git Forensics",
        "stage": "VERIFY",
        "objective": "Audit commit timeline, provenance, and check for single-dump paste patterns",
        "status": "COMPLETED",
        "tool": "git_provenance_auditor",
        "observation": "14 commits spanning 3 weeks. Incremental development cadence from base abstractions to complex OOD mathematics and unit tests.",
        "output": "Git authenticity verified: Natural engineering progression with authentic author commit signatures.",
        "timestamp": "10:31:08",
    },
    {
        "agent": "Originality Investigation",
        "stage": "VERIFY",
        "objective": "Check AST similarity indicators against known public tutorial snippets",
        "status": "COMPLETED",
        "tool": "ast_similarity_scanner",
        "observation": "Similarity index: 6.2% (standard library boilerplate & PyTorch nn.Module init patterns). Zero verbatim tutorial duplicates.",
        "output": "No significant similarity anomalies detected. Codebase reflects original implementation.",
        "timestamp": "10:31:19",
    },
    {
        "agent": "Skill Evaluator",
        "stage": "VERIFY",
        "objective": "Aggregate multi-agent evidence into normalized skill scores",
        "status": "COMPLETED",
        "tool": "skill_scoring_matrix",
        "observation": "All 7 claimed skills substantiated by verifiable source files, passing pytest cases, and authentic git commits.",
        "output": "Overall Evidence Score: 94/100. Verdict: VERIFIED. Recommended for technical viva.",
        "timestamp": "10:31:30",
    },
    {
        "agent": "Viva Generator",
        "stage": "VERIFY",
        "objective": "Formulate deep architectural viva inquiries based on candidate's actual code",
        "status": "COMPLETED",
        "tool": "viva_synthesis_engine",
        "observation": "Targeted key architectural decisions in aegis/uncertainty/monte_carlo.py, aegis/ood/mahalanobis.py, and aegis/drift/drift_detector.py.",
        "output": "Compiled 3 targeted technical questions for candidate interview.",
        "timestamp": "10:31:40",
    },
]

AEGIS_SKILL_ASSESSMENT = {
    "overall_score": 94,
    "verdict": "VERIFIED",
    "confidence": "High",
    "skills": {
        "Python": {
            "impl_score": 96,
            "test_score": 95,
            "arch_evidence": "Clean PEP 8 idiomatic code, type hints, context managers, and custom exceptions.",
            "git_evidence": "Incremental commits adding modules over 3 weeks.",
            "viva_score": 96,
            "coverage": 95,
            "verdict": "VERIFIED",
            "supporting_files": [
                "aegis/core/base.py",
                "aegis/uncertainty/monte_carlo.py",
                "tests/test_uncertainty.py",
            ],
            "missing_evidence": "None. Excellent Python 3.11 usage.",
            "limitations": "Does not enforce strict MyPy static typing flags.",
        },
        "OOP": {
            "impl_score": 94,
            "test_score": 92,
            "arch_evidence": "Abstract Base Class BaseDetector with inheritance polymorphism for all detectors.",
            "git_evidence": "Base classes defined in initial commit, extended by downstream modules.",
            "viva_score": 94,
            "coverage": 92,
            "verdict": "VERIFIED",
            "supporting_files": ["aegis/core/base.py", "aegis/ood/mahalanobis.py"],
            "missing_evidence": "Multiple inheritance not demonstrated (clean single-inheritance preferred).",
            "limitations": "Clean design.",
        },
        "Machine Learning": {
            "impl_score": 95,
            "test_score": 94,
            "arch_evidence": "Monte Carlo Dropout, Class-conditional Mahalanobis OOD distance, Two-sample KS test.",
            "git_evidence": "Mathematical equations converted to vectorized NumPy / PyTorch operations.",
            "viva_score": 97,
            "coverage": 94,
            "verdict": "VERIFIED",
            "supporting_files": [
                "aegis/uncertainty/monte_carlo.py",
                "aegis/ood/mahalanobis.py",
                "aegis/drift/drift_detector.py",
            ],
            "missing_evidence": "No fine-tuning pipeline for large language models.",
            "limitations": "Focused on tabular, computer vision, and embeddings guardrails.",
        },
        "Software Architecture": {
            "impl_score": 93,
            "test_score": 90,
            "arch_evidence": "Layered separation: Core -> Detection -> Scoring -> Recommendation.",
            "git_evidence": "Modular directory structure organized from day 1.",
            "viva_score": 92,
            "coverage": 90,
            "verdict": "VERIFIED",
            "supporting_files": [
                "aegis/core/base.py",
                "aegis/scoring/risk_engine.py",
            ],
            "missing_evidence": "No microservices gRPC interface.",
            "limitations": "Library architecture rather than distributed server.",
        },
        "Testing": {
            "impl_score": 92,
            "test_score": 100,
            "arch_evidence": "18 pytest test cases with fixtures and numerical assertions.",
            "git_evidence": "Dedicated test commit after each feature release.",
            "viva_score": 94,
            "coverage": 88,
            "verdict": "VERIFIED",
            "supporting_files": ["tests/test_uncertainty.py"],
            "missing_evidence": "End-to-end integration test with live external API.",
            "limitations": "Unit and property tests well-represented.",
        },
        "Git/GitHub": {
            "impl_score": 90,
            "test_score": 90,
            "arch_evidence": "GitHub Actions CI workflow, semantic commit conventions.",
            "git_evidence": "14 clear commits with feature prefixes and incremental diffs.",
            "viva_score": 90,
            "coverage": 90,
            "verdict": "VERIFIED",
            "supporting_files": [".github/workflows/ci.yml", "README.md"],
            "missing_evidence": "No multi-author pull request merge reviews.",
            "limitations": "Solo contributor repository.",
        },
        "API Development": {
            "impl_score": 88,
            "test_score": 85,
            "arch_evidence": "Clean functional API with consistent .fit(), .score(), .evaluate_safety() interfaces.",
            "git_evidence": "Wrapper classes for Scikit-learn and PyTorch pipelines.",
            "viva_score": 90,
            "coverage": 84,
            "verdict": "VERIFIED",
            "supporting_files": ["aegis/core/base.py", "aegis/wrappers"],
            "missing_evidence": "FastAPI REST API wrapper is planned in v2 roadmap.",
            "limitations": "Exposes Python SDK API, not HTTP REST endpoints.",
        },
    },
}

AEGIS_VIVA_QUESTIONS = [
    {
        "id": "Q1",
        "question": "In `aegis/uncertainty/monte_carlo.py`, how does retaining active dropout during test inference (`self.model.train()`) mathematically approximate a variational Bayesian posterior over weights?",
        "difficulty": "Advanced",
        "source_file": "aegis/uncertainty/monte_carlo.py",
        "function": "estimate_uncertainty",
        "context": "Gal & Ghahramani (2016) demonstrated that dropout in neural networks acts as a variational approximation to a Gaussian process. Candidate explicitly called `model.train()` before stochastic evaluation.",
        "sample_answer": "Standard neural networks compute deterministic point estimates. By leaving dropout active during inference, each forward pass randomly zeroes distinct weight subsets, effectively sampling from a Bernoulli variational distribution over network topologies. The sample variance across N iterations estimates epistemic uncertainty.",
        "expected_concepts": [
            "Variational inference",
            "Epistemic uncertainty",
            "Stochastic forward passes",
            "Sample variance across predictions",
        ],
        "evaluation": {
            "technical_correctness": 96,
            "understanding": 98,
            "reasoning": 95,
            "evidence_alignment": 97,
            "limitations_awareness": 92,
            "overall_score": 96.0,
            "feedback": "Flawless theoretical and practical explanation. Candidate demonstrated deep mastery of why dropout must stay enabled at inference time.",
            "follow_up": "How did you calibrate the choice of N=30 samples balancing inference latency against variance convergence?",
        },
    },
    {
        "id": "Q2",
        "question": "In `aegis/ood/mahalanobis.py`, why did you implement class-conditional Mahalanobis distance with a shared pooled covariance matrix rather than fitting a separate covariance for each class?",
        "difficulty": "Advanced",
        "source_file": "aegis/ood/mahalanobis.py",
        "function": "fit & score",
        "context": "Line 25 pools empirical covariance across classes and adds a regularization ridge `1e-5 * I` to guarantee invertibility.",
        "sample_answer": "Fitting independent covariance matrices per class often leads to numerical rank deficiency and overfitting when individual classes have limited sample counts in high-dimensional feature spaces. Using a shared pooled covariance regularized with an epsilon ridge guarantees full rank and positive definiteness while preserving class-specific centroids.",
        "expected_concepts": [
            "Pooled covariance",
            "High-dimensional singularity",
            "Ridge regularization",
            "Class centroid distance",
        ],
        "evaluation": {
            "technical_correctness": 95,
            "understanding": 96,
            "reasoning": 94,
            "evidence_alignment": 95,
            "limitations_awareness": 94,
            "overall_score": 95.0,
            "feedback": "Accurately articulates the bias-variance tradeoff in covariance estimation for out-of-distribution detection.",
            "follow_up": "What is the computational complexity of inverting the pooled covariance matrix as feature dimensions scale?",
        },
    },
    {
        "id": "Q3",
        "question": "In `aegis/drift/drift_detector.py`, what guided your choice of the two-sample Kolmogorov-Smirnov test over Population Stability Index (PSI) for continuous feature drift monitoring?",
        "difficulty": "Intermediate",
        "source_file": "aegis/drift/drift_detector.py",
        "function": "check_drift",
        "context": "Non-parametric empirical cumulative distribution function comparison without arbitrary binning.",
        "sample_answer": "The two-sample KS test is completely non-parametric and sensitive to changes in both shape, location, and scale of continuous distributions without requiring arbitrary discretization into histogram bins. PSI is heavily dependent on binning choices, which can mask subtle drift in tail distributions.",
        "expected_concepts": [
            "Non-parametric hypothesis testing",
            "Empirical CDF comparison",
            "Arbitrary binning avoidance",
            "Tail sensitivity",
        ],
        "evaluation": {
            "technical_correctness": 94,
            "understanding": 95,
            "reasoning": 93,
            "evidence_alignment": 94,
            "limitations_awareness": 90,
            "overall_score": 93.5,
            "feedback": "Sound reasoning highlighting the pitfalls of manual binning on continuous feature representations.",
            "follow_up": "How do you control the family-wise error rate when evaluating KS drift across hundreds of input features simultaneously?",
        },
    },
]


def get_default_aegis_session() -> Dict[str, Any]:
    """Retrieve canonical AegisAI session for CAND-001."""
    session_id = "sess_aegis_cand001_live"
    cred_payload = {
        "credential_id": "SP-CRED-2026-AEGIS-01",
        "candidate_id": "CAND-001",
        "repo_url": "https://github.com/arshavardhan/AegisAi",
        "commit_sha": "e4b971a8f9c08d234a11b6f0e9e4a8f9d0c2b1e7",
        "verified_skills": [
            {"skill": "Python", "score": 96, "verdict": "VERIFIED"},
            {"skill": "OOP", "score": 94, "verdict": "VERIFIED"},
            {
                "skill": "Machine Learning",
                "score": 95,
                "verdict": "VERIFIED",
            },
            {
                "skill": "Software Architecture",
                "score": 93,
                "verdict": "VERIFIED",
            },
            {"skill": "Testing", "score": 92, "verdict": "VERIFIED"},
            {"skill": "Git/GitHub", "score": 90, "verdict": "VERIFIED"},
            {
                "skill": "API Development",
                "score": 88,
                "verdict": "VERIFIED",
            },
        ],
        "overall_evidence_score": 94,
        "viva_average_score": 95.0,
        "issue_timestamp": "2026-10-31T10:32:00Z",
        "issuer": "SkillProof AI Verification Authority (Grand Finale Edition)",
        "signature_algorithm": "HMAC-SHA256",
        "status": "VALID",
    }
    sig = compute_signature(cred_payload)

    return {
        "session_id": session_id,
        "candidate_id": "CAND-001",
        "repo_url": "https://github.com/arshavardhan/AegisAi",
        "claimed_skills": [
            "Python",
            "OOP",
            "Machine Learning",
            "Software Architecture",
            "Testing",
            "Git/GitHub",
            "API Development",
        ],
        "description": "AegisAI - Advanced AI Guardrails & Model Governance Framework",
        "status": "completed",
        "approval_status": "approved",
        "repo_info": AEGIS_REPO_INFO,
        "code_files": AEGIS_CODE_FILES,
        "git_commits": AEGIS_GIT_COMMITS,
        "timeline": AEGIS_AGENT_TRAJECTORY,
        "skill_assessment": AEGIS_SKILL_ASSESSMENT,
        "viva_questions": AEGIS_VIVA_QUESTIONS,
        "approval": {
            "decision": "approved",
            "reviewer_notes": "Exemplary engineering. 18 passing tests, clean BaseDetector polymorphism, robust Monte Carlo dropout sampling, and authentic multi-week git commits.",
            "reviewer_id": "auditor_lead_01",
            "timestamp": "2026-10-31T10:31:50Z",
        },
        "credential": {
            "credential_id": "SP-CRED-2026-AEGIS-01",
            "data": cred_payload,
            "signature": sig,
            "status": "VALID",
        },
    }


def get_empty_session() -> Dict[str, Any]:
    """Retrieve clean empty candidate session with no hardcoded repository or candidate details."""
    return {
        "session_id": "",
        "candidate_id": "",
        "repo_url": "",
        "claimed_skills": [],
        "description": "",
        "status": "NOT_STARTED",
        "approval_status": "pending",
        "repo_info": {
            "repo_name": "",
            "repo_url": "",
            "commit_sha": "",
            "default_branch": "main",
            "languages": {},
            "dependencies": [],
            "discovered_modules": [],
            "ci_config": "",
            "readme_summary": "",
        },
        "code_files": {},
        "git_commits": [],
        "timeline": [],
        "skill_assessment": {
            "overall_score": 0,
            "verdict": "PENDING",
            "confidence": "None",
            "skills": {},
        },
        "viva_questions": [],
        "approval": {},
        "credential": {},
    }


class SessionManager:
    """Manages active candidate state, session caching, and fallback persistence."""

    @staticmethod
    def init_session():
        """Ensure all required session state variables are initialized."""
        if "active_session" not in st.session_state:
            st.session_state["active_session"] = get_empty_session()

        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "Overview"

        if "backend_url" not in st.session_state:
            from config import DEFAULT_BACKEND_URL
            st.session_state["backend_url"] = DEFAULT_BACKEND_URL

        if "backend_connected" not in st.session_state:
            st.session_state["backend_connected"] = False

        if "uploaded_resume_name" not in st.session_state:
            st.session_state["uploaded_resume_name"] = None

        if "uploaded_resume_text" not in st.session_state:
            st.session_state["uploaded_resume_text"] = None

        if "parsed_resume_profile" not in st.session_state:
            st.session_state["parsed_resume_profile"] = None

        if "resume_extracted_skills" not in st.session_state:
            st.session_state["resume_extracted_skills"] = []

        if "selected_candidate_id" not in st.session_state:
            st.session_state["selected_candidate_id"] = ""

        if "selected_repo_url" not in st.session_state:
            st.session_state["selected_repo_url"] = ""

        if "selected_repository_url" not in st.session_state:
            st.session_state["selected_repository_url"] = ""

        if "selected_repository_owner" not in st.session_state:
            st.session_state["selected_repository_owner"] = ""

        if "selected_repository_name" not in st.session_state:
            st.session_state["selected_repository_name"] = ""

        if "selected_claimed_skills" not in st.session_state:
            st.session_state["selected_claimed_skills"] = []

        if "selected_description" not in st.session_state:
            st.session_state["selected_description"] = ""

        if "selected_candidate_description" not in st.session_state:
            st.session_state["selected_candidate_description"] = ""

        if "is_verification_prepared" not in st.session_state:
            st.session_state["is_verification_prepared"] = False

    @staticmethod
    def get_session() -> Dict[str, Any]:
        SessionManager.init_session()
        return st.session_state["active_session"]

    @staticmethod
    def set_session(session_data: Dict[str, Any]):
        st.session_state["active_session"] = session_data

    @staticmethod
    def clear_session():
        """Reset the current candidate and repository selection completely."""
        st.session_state["active_session"] = get_empty_session()
        st.session_state["selected_candidate_id"] = ""
        st.session_state["selected_repo_url"] = ""
        st.session_state["selected_repository_url"] = ""
        st.session_state["selected_repository_owner"] = ""
        st.session_state["selected_repository_name"] = ""
        st.session_state["selected_claimed_skills"] = []
        st.session_state["selected_description"] = ""
        st.session_state["selected_candidate_description"] = ""
        st.session_state["uploaded_resume_name"] = None
        st.session_state["uploaded_resume_text"] = None
        st.session_state["parsed_resume_profile"] = None
        st.session_state["resume_extracted_skills"] = []
        st.session_state["is_verification_prepared"] = False
