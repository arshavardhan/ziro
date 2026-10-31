import pytest
import sqlite3
from pathlib import Path
from rag.chunker import chunk_python, chunk_text, chunk_repository
from rag.embeddings import embed_text, _deterministic_fallback_embed
from rag.vector_store import index_repository, search, get_chunks_count, ensure_tables
from rag.retriever import retrieve_for_skill, chunks_to_evidence_items, get_skill_query
from agents.graph import (
    build_assessment_graph,
    route_investigation,
    AssessmentState
)
from langgraph.checkpoint.sqlite import SqliteSaver
import config

def test_rag_ast_chunking():
    source = """class ModelTrainer:
    def __init__(self, lr=0.01):
        self.lr = lr

    def train(self, data):
        return [x * self.lr for x in data]

def evaluate(model, test_data):
    return sum(test_data)
"""
    chunks = chunk_python("ml/trainer.py", source)
    assert len(chunks) >= 3
    symbols = {c["symbol"] for c in chunks}
    assert "ModelTrainer" in symbols
    assert "ModelTrainer.train" in symbols
    assert "evaluate" in symbols
    
    trainer_chunk = next(c for c in chunks if c["symbol"] == "ModelTrainer.train")
    assert trainer_chunk["line_start"] == 5
    assert trainer_chunk["line_end"] == 6
    assert trainer_chunk["language"] == "Python"
    assert "self.lr" in trainer_chunk["content"]

def test_rag_text_chunking():
    source = "\n".join(f"line_{i}" for i in range(1, 101))
    chunks = chunk_text("notes.txt", source, language="Text", chunk_size=40, overlap=10)
    assert len(chunks) == 3
    assert chunks[0]["line_start"] == 1
    assert chunks[0]["line_end"] == 40
    assert chunks[1]["line_start"] == 31
    assert chunks[1]["line_end"] == 70

def test_rag_vector_store_cross_session_isolation(tmp_path, monkeypatch):
    test_db = tmp_path / "rag_test.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    
    files_a = {"service.py": "def process_payment(amount):\n    return amount * 1.05\n"}
    files_b = {"model.py": "def predict_drift(feature_vector):\n    return sum(feature_vector)\n"}
    
    index_repository("session_A", "sha_A"*10, files_a)
    index_repository("session_B", "sha_B"*10, files_b)
    
    # Query for 'payment' in session A must find service.py
    results_a = search("session_A", "sha_A"*10, "payment processing")
    assert len(results_a) > 0
    assert "service.py" in results_a[0]["file"]
    
    # Query in session B must strictly NOT contain any files or chunks from session A
    results_b = search("session_B", "sha_B"*10, "payment processing")
    assert not any("service.py" in r["file"] for r in results_b)
    assert all(r["chunk_id"].startswith("session_B:") for r in results_b)
    
    # Unrelated query with threshold in session B returns zero
    assert len(search("session_B", "sha_B"*10, "payment processing", min_score=0.6)) == 0

def test_rag_skill_retrieval_and_traceability(tmp_path, monkeypatch):
    test_db = tmp_path / "rag_test2.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    
    files = {
        "drift/detector.py": "class DriftDetector:\n    def calculate_ks(self, d1, d2):\n        return 0.05\n",
        "tests/test_drift.py": "def test_drift():\n    assert True\n"
    }
    index_repository("session_ML", "sha_ML"*10, files)
    
    chunks = retrieve_for_skill("session_ML", "sha_ML"*10, "Machine Learning", top_k=2)
    assert len(chunks) > 0
    
    evidence = chunks_to_evidence_items("session_ML", "CAND-001", "sha_ML"*10, "Machine Learning", chunks)
    assert len(evidence) > 0
    item = evidence[0]
    assert item["assessment_id"] == "session_ML"
    assert item["candidate_id"] == "CAND-001"
    assert item["claimed_skills"] == ["Machine Learning"]
    assert item["file"] in {"drift/detector.py", "tests/test_drift.py"}
    assert item["line_start"] >= 1
    assert item["line_end"] >= item["line_start"]
    assert item["collection_tool"] == "rag_semantic_retriever"

def test_langgraph_compilation():
    graph = build_assessment_graph()
    assert graph is not None
    node_names = set(graph.nodes.keys())
    expected_nodes = {
        "initialize",
        "validate_url",
        "acquire_repository",
        "analyze_source_code",
        "index_repository_rag",
        "retrieve_skill_evidence_rag",
        "plan_investigation",
        "execute_investigation",
        "reflect_and_replan",
        "evaluate_skills",
        "generate_viva",
        "finalize_assessment"
    }
    assert expected_nodes.issubset(node_names)

def test_langgraph_routing_decisions():
    # 1. More actions and under max cycles -> continue investigation
    state_continue: AssessmentState = {
        "investigation_cycles": 1,
        "max_cycles": 3,
        "current_plan": {"stop": False, "actions": [{"tool": "find_tests"}]}
    }
    assert route_investigation(state_continue) == "execute_investigation"
    
    # 2. Plan explicitly stops -> advance to evaluate skills
    state_stop: AssessmentState = {
        "investigation_cycles": 1,
        "max_cycles": 3,
        "current_plan": {"stop": True, "actions": []}
    }
    assert route_investigation(state_stop) == "evaluate_skills"
    
    # 3. Max cycles reached -> advance to evaluate skills
    state_budget: AssessmentState = {
        "investigation_cycles": 3,
        "max_cycles": 3,
        "current_plan": {"stop": False, "actions": [{"tool": "find_tests"}]}
    }
    assert route_investigation(state_budget) == "evaluate_skills"

def test_langgraph_sqlite_checkpointing(tmp_path):
    checkpoint_db = tmp_path / "langgraph_checkpoints.sqlite3"
    conn = sqlite3.connect(str(checkpoint_db), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    
    graph = build_assessment_graph(checkpointer=saver)
    assert graph is not None
