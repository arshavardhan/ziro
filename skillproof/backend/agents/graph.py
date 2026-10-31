"""LangGraph StateGraph for SkillProof AI Autonomous Verification Pipeline.
Implements typed AssessmentState, granular nodes, RAG retrieval, and dynamic replanning loop.
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from pathlib import Path
import time
import uuid
import sqlite3

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

import config
from core.guardrails import validate_url
from core.exceptions import AppError
from core.state_machine import transition
from database import repositories as memory
from agents import (
    repository_agent,
    code_agent,
    test_agent,
    git_agent,
    originality_agent,
    skill_evaluator,
    viva_generator,
    planner
)
from services.evidence_service import attach_results, implementation_evidence
from services.scoring_service import calculate
from services.provenance_service import freeze_baseline, enrich_evidence
from tools.dependency_tool import relationships
from rag.vector_store import index_repository as rag_index_repo, get_chunks_count
from rag.retriever import retrieve_for_skill, chunks_to_evidence_items

class AssessmentState(TypedDict, total=False):
    session_id: str
    candidate_id: str
    github_url: str
    requested_sha: Optional[str]
    claimed_skills: List[str]
    current_status: str
    error: Optional[str]
    stop_reason: Optional[str]
    
    # Workspace & snapshot
    workspace_path: Optional[str]
    repository_commit_sha: Optional[str]
    repository_snapshot: Dict[str, Any]
    files: Dict[str, str]
    languages: List[str]
    dependencies: List[str]
    
    # Static & Dynamic findings
    code_evidence: List[Dict[str, Any]]
    evidence_graph: List[Dict[str, Any]]
    commit_summary: Dict[str, Any]
    similarity_findings: List[Dict[str, Any]]
    test_results: Dict[str, Any]
    baseline: Dict[str, Any]
    
    # RAG state
    rag_indexed: bool
    rag_chunks_count: int
    rag_evidence: Dict[str, List[Dict[str, Any]]]
    
    # Dynamic Agent Cycles (PLAN -> ACT -> OBSERVE -> REFLECT -> REPLAN)
    investigation_cycles: int
    max_cycles: int
    missing_evidence: List[str]
    agent_cycles: List[Dict[str, Any]]
    current_plan: Optional[Dict[str, Any]]
    
    # Evaluations & Viva
    assessments: List[Dict[str, Any]]
    skill_scores: Dict[str, Any]
    viva_questions: List[Dict[str, Any]]
    limitations: List[str]

# --- Graph Nodes ---

def node_initialize(state: AssessmentState) -> Dict[str, Any]:
    """Initialize assessment state, validate session record."""
    sid = state["session_id"]
    data = memory.get(sid)
    if data["current_status"] == "QUEUED":
        transition(data, "PLANNING")
        memory.save(data)
    
    return {
        "current_status": "PLANNING",
        "investigation_cycles": data.get("investigation_cycles", 0),
        "max_cycles": config.MAX_CYCLES,
        "missing_evidence": data.get("missing_evidence", []),
        "agent_cycles": data.get("agent_cycles", []),
        "code_evidence": data.get("code_evidence", []),
        "evidence_graph": data.get("evidence_graph", []),
        "rag_indexed": False,
        "rag_chunks_count": 0,
        "rag_evidence": {}
    }

def node_validate_url(state: AssessmentState) -> Dict[str, Any]:
    """Validate public GitHub URL safely."""
    clean_url = validate_url(state["github_url"])
    return {"github_url": clean_url}

def node_acquire_repository(state: AssessmentState) -> Dict[str, Any]:
    """Acquire repository clone or resume existing pinned workspace."""
    sid = state["session_id"]
    data = memory.get(sid)
    checkpoint = data.get("_checkpoint", {})
    
    if checkpoint.get("repository"):
        root, files, snapshot = repository_agent.resume(
            Path(data["_workspace"]),
            data["github_url"],
            data["repository_commit_sha"]
        )
    else:
        workspace = sid + "-" + uuid.uuid4().hex[:8]
        root, files, snapshot = repository_agent.run(
            data["github_url"],
            workspace,
            state.get("requested_sha")
        )
        data.update(
            repository_snapshot=snapshot,
            repository_commit_sha=snapshot["commit_sha"],
            _workspace=str(root)
        )
        checkpoint["repository"] = True
        memory.save(data, [("repository_snapshots", snapshot), ("repository_files", list(files))])

    return {
        "workspace_path": str(root),
        "repository_commit_sha": snapshot["commit_sha"],
        "repository_snapshot": snapshot,
        "files": files,
        "languages": snapshot.get("languages", []),
        "dependencies": snapshot.get("dependencies", [])
    }

def node_analyze_source_code(state: AssessmentState) -> Dict[str, Any]:
    """Perform deterministic AST source inspection."""
    sid = state["session_id"]
    data = memory.get(sid)
    files = state["files"]
    sha = state["repository_commit_sha"]
    checkpoint = data.get("_checkpoint", {})

    if not checkpoint.get("baseline"):
        evidence, edges = code_agent.inspect(files, sha)
        by_id = {e["evidence_id"]: e for e in state.get("code_evidence", [])}
        by_id.update({e["evidence_id"]: e for e in evidence})
        updated_evidence = list(by_id.values())
        all_edges = state.get("evidence_graph", []) + edges
        updated_edges = list({(e["source"], e["target"], e["relation"]): e for e in all_edges}.values())
        
        data["code_evidence"] = updated_evidence
        data["evidence_graph"] = updated_edges
        data["_source_collected_at"] = memory.now()
        enrich_evidence(data)
        
        # Git history analysis
        commit_summary = git_agent.run(Path(state["workspace_path"]), sha)
        data["commit_summary"] = commit_summary
        
        # Structural similarity
        similarity_findings = originality_agent.run(files)
        data["similarity_findings"] = similarity_findings
        
        # Initial test run/discovery
        test_results = test_agent.run(Path(state["workspace_path"]), files, updated_edges)
        data["test_results"] = test_results
        
        checkpoint["tests"] = True
        checkpoint["baseline"] = True
        memory.save(data, [
            ("git_findings", commit_summary),
            ("test_results", test_results),
            ("skill_evidence", updated_evidence),
            ("similarity_findings", similarity_findings)
        ])
        baseline = freeze_baseline(data)
        data["baseline"] = baseline
        memory.save(data)
        
        return {
            "code_evidence": updated_evidence,
            "evidence_graph": updated_edges,
            "commit_summary": commit_summary,
            "similarity_findings": similarity_findings,
            "test_results": test_results,
            "baseline": baseline
        }
    else:
        return {
            "code_evidence": data.get("code_evidence", []),
            "evidence_graph": data.get("evidence_graph", []),
            "commit_summary": data.get("commit_summary", {}),
            "similarity_findings": data.get("similarity_findings", []),
            "test_results": data.get("test_results", {}),
            "baseline": data.get("baseline", {})
        }

def node_index_repository_rag(state: AssessmentState) -> Dict[str, Any]:
    """Ingest repository into session-isolated SQLite vector store."""
    sid = state["session_id"]
    sha = state["repository_commit_sha"]
    files = state["files"]
    
    idx_summary = rag_index_repo(sid, sha, files)
    chunks_cnt = get_chunks_count(sid, sha)
    
    return {
        "rag_indexed": True,
        "rag_chunks_count": chunks_cnt
    }

def node_retrieve_skill_evidence_rag(state: AssessmentState) -> Dict[str, Any]:
    """RAG Retrieval: ground claimed skills against indexed repository chunks."""
    sid = state["session_id"]
    sha = state["repository_commit_sha"]
    candidate_id = state.get("candidate_id", "CANDIDATE")
    claimed_skills = state.get("claimed_skills", [])
    
    rag_evidence = {}
    new_evidence_items = []
    
    for skill in claimed_skills:
        chunks = retrieve_for_skill(sid, sha, skill, top_k=3)
        rag_evidence[skill] = chunks
        items = chunks_to_evidence_items(sid, candidate_id, sha, skill, chunks)
        new_evidence_items.extend(items)
        
    by_id = {e["evidence_id"]: e for e in state.get("code_evidence", [])}
    by_id.update({e["evidence_id"]: e for e in new_evidence_items})
    merged_evidence = list(by_id.values())
    
    data = memory.get(sid)
    data["code_evidence"] = merged_evidence
    memory.save(data)
    
    return {
        "rag_evidence": rag_evidence,
        "code_evidence": merged_evidence
    }

def node_plan_investigation(state: AssessmentState) -> Dict[str, Any]:
    """Agent PLAN: Formulate investigation actions based on repository inventory and baseline."""
    sid = state["session_id"]
    data = memory.get(sid)
    checkpoint = data.get("_checkpoint", {})
    
    if not checkpoint.get("plan"):
        plan = planner.plan({
            "url": state["github_url"],
            "skills": state["claimed_skills"],
            "baseline": state.get("baseline"),
            "inventory": list(state["files"].keys()),
            "evidence": skill_evaluator.compact(state["code_evidence"])
        })
        checkpoint["plan"] = True
        data["analysis_plan"] = plan
        memory.save(data, [("agent_plans", plan)])
    else:
        plan = data["analysis_plan"]

    if data["current_status"] == "PLANNING":
        transition(data, "ANALYSING")
        memory.save(data)
        
    return {
        "current_status": "ANALYSING",
        "current_plan": plan
    }

def node_execute_investigation(state: AssessmentState) -> Dict[str, Any]:
    """Agent ACT & OBSERVE: Execute tools selected by the planner."""
    sid = state["session_id"]
    data = memory.get(sid)
    plan = state.get("current_plan") or {}
    actions = plan.get("actions", [])
    cycle_num = state.get("investigation_cycles", 0) + 1
    
    cycle = {
        "cycle_number": cycle_num,
        "started_at": memory.now(),
        "finished_at": None,
        "plan": plan,
        "decision_summary": plan.get("rationale", "Executing selected investigation tools"),
        "selected_tools": [a.get("tool") for a in actions],
        "executions": [],
        "observations": {},
        "replanning_decision": None,
        "stop_reason": None
    }
    
    root = Path(state["workspace_path"])
    files = state["files"]
    sha = state["repository_commit_sha"]
    
    for action in actions:
        try:
            evidence, edges, observation = code_agent.act(root, files, sha, action)
            by_id = {e["evidence_id"]: e for e in state["code_evidence"]}
            by_id.update({e["evidence_id"]: e for e in evidence})
            state["code_evidence"] = list(by_id.values())
            state["evidence_graph"] = list({(e["source"], e["target"], e["relation"]): e for e in (state["evidence_graph"] + edges)}.values())
            
            cycle["executions"].append({
                "tool": action["tool"],
                "inputs": action,
                "status": "completed",
                "outputs": observation,
                "evidence_ids": [e["evidence_id"] for e in evidence]
            })
        except Exception as exc:
            cycle["executions"].append({
                "tool": action.get("tool", "unknown"),
                "inputs": action,
                "status": "failed",
                "error": str(exc)
            })
            cycle["replanning_decision"] = "Tool error encountered; replan remaining investigation within budget."
            break

    cycle["finished_at"] = memory.now()
    cycle["observations"] = {
        "evidence_count": len(state["code_evidence"]),
        "missing_evidence": state.get("missing_evidence", [])
    }
    
    data["code_evidence"] = state["code_evidence"]
    data["evidence_graph"] = state["evidence_graph"]
    data.setdefault("agent_cycles", []).append(cycle)
    data["investigation_cycles"] = cycle_num
    memory.save(data)
    
    return {
        "investigation_cycles": cycle_num,
        "agent_cycles": data["agent_cycles"],
        "code_evidence": state["code_evidence"],
        "evidence_graph": state["evidence_graph"]
    }

def node_reflect_and_replan(state: AssessmentState) -> Dict[str, Any]:
    """Agent REFLECT & REPLAN: Critique current findings and decide next actions."""
    sid = state["session_id"]
    data = memory.get(sid)
    cycle_num = state.get("investigation_cycles", 0)
    
    if cycle_num >= state.get("max_cycles", config.MAX_CYCLES):
        stop_reason = "INVESTIGATION_BUDGET_EXHAUSTED"
        if data.get("agent_cycles"):
            data["agent_cycles"][-1]["stop_reason"] = stop_reason
        data["stop_reason"] = stop_reason
        memory.save(data)
        return {
            "stop_reason": stop_reason,
            "current_plan": {"stop": True, "actions": [], "rationale": "Max cycles reached", "missing_evidence": state.get("missing_evidence", [])}
        }
        
    next_plan = planner.critique({
        "skills": state["claimed_skills"],
        "inventory": list(state["files"].keys()),
        "evidence": skill_evaluator.compact(state["code_evidence"]),
        "relationships": state["evidence_graph"][:100],
        "previous_gaps": state.get("missing_evidence", []),
        "cycle": cycle_num
    })
    
    data["missing_evidence"] = next_plan.get("missing_evidence", [])
    memory.record(data, "planner", "RE-PLAN", next_plan, events=[("agent_plans", next_plan)])
    memory.record(data, "planner", "REFLECT", {
        "decision_summary": next_plan["rationale"],
        "missing_evidence": next_plan.get("missing_evidence", [])
    })
    
    if next_plan.get("stop") or not next_plan.get("actions"):
        stop_reason = "EVIDENCE_SUFFICIENT" if not next_plan.get("missing_evidence") else "NO_USEFUL_ACTIONS"
        data["stop_reason"] = stop_reason
        if data.get("agent_cycles"):
            data["agent_cycles"][-1]["replanning_decision"] = next_plan["rationale"]
            data["agent_cycles"][-1]["stop_reason"] = stop_reason
        data.setdefault("_checkpoint", {})["investigation_done"] = True
        memory.save(data)
        return {
            "stop_reason": stop_reason,
            "missing_evidence": data["missing_evidence"],
            "current_plan": next_plan
        }
    
    memory.save(data)
    return {
        "missing_evidence": data["missing_evidence"],
        "current_plan": next_plan
    }

def route_investigation(state: AssessmentState) -> Literal["execute_investigation", "evaluate_skills"]:
    """Conditional router based on replanning decision and iteration limits."""
    plan = state.get("current_plan") or {}
    if plan.get("stop") or not plan.get("actions"):
        return "evaluate_skills"
    if state.get("investigation_cycles", 0) >= state.get("max_cycles", config.MAX_CYCLES):
        return "evaluate_skills"
    return "execute_investigation"

def node_evaluate_skills(state: AssessmentState) -> Dict[str, Any]:
    """Skill evaluation: multi-factor scoring grounded in static findings and RAG evidence."""
    sid = state["session_id"]
    data = memory.get(sid)
    
    if data["current_status"] in {"PLANNING", "ANALYSING"}:
        transition(data, "TESTING")
        memory.save(data)
    if data["current_status"] == "TESTING":
        transition(data, "EVALUATING")
        memory.save(data)

    checkpoint = data.setdefault("_checkpoint", {})
    if not checkpoint.get("assessment"):
        assessments = skill_evaluator.run(
            state["claimed_skills"],
            state["code_evidence"],
            state["evidence_graph"],
            state["test_results"],
            state["commit_summary"]
        )
        checkpoint["assessment"] = True
        data["assessments"] = assessments
        memory.save(data, [("skill_evidence", assessments)])
        enrich_evidence(data)
    else:
        assessments = data.get("assessments", [])

    return {
        "current_status": "EVALUATING",
        "assessments": assessments
    }

def node_generate_viva(state: AssessmentState) -> Dict[str, Any]:
    """Generate repository-grounded technical viva questions citing source evidence."""
    sid = state["session_id"]
    data = memory.get(sid)
    checkpoint = data.setdefault("_checkpoint", {})
    
    if not checkpoint.get("questions"):
        questions = viva_generator.run(state["code_evidence"])
        by_id = {e["evidence_id"]: e for e in state["code_evidence"]}
        for q in questions:
            item = by_id.get(q["evidence_reference"])
            if item:
                q.update(
                    line_start=item["line_start"],
                    line_end=item["line_end"],
                    related_evidence_ids=[item["evidence_id"]],
                    skill=next(iter(item.get("claimed_skills", [])), None)
                )
        checkpoint["questions"] = True
        data["viva_questions"] = questions
        memory.save(data, [("viva_questions", questions)])
    else:
        questions = data.get("viva_questions", [])

    return {"viva_questions": questions}

def node_finalize_assessment(state: AssessmentState) -> Dict[str, Any]:
    """Generate final report, calculate multi-factor scores, transition to VIVA_PENDING."""
    sid = state["session_id"]
    data = memory.get(sid)
    
    data["limitations"] = [
        "Repository evidence does not establish candidate identity or personal authorship.",
        "This assessment evaluates available evidence, not the candidate's entire professional capability.",
        "Test definitions are not executed tests or coverage; inspect the independent execution status.",
        "Static call graph is partial; dynamic dispatch and all data flow are not resolved.",
        "No internet-wide plagiarism or reliable AI-authorship detection is performed."
    ]
    calculate(data)
    transition(data, "VIVA_PENDING")
    data.setdefault("_checkpoint", {})["analysis_complete"] = True
    memory.save(data)
    memory.record(data, "orchestrator", "VERIFY", {
        "status": data["current_status"],
        "cycles": data.get("investigation_cycles", 0),
        "llm_calls": data.get("llm_calls", 0)
    })
    
    return {
        "current_status": "VIVA_PENDING",
        "skill_scores": data.get("skill_scores", {}),
        "limitations": data["limitations"]
    }

# --- Graph Assembly & Compilation ---

def build_assessment_graph(checkpointer: Optional[SqliteSaver] = None) -> Any:
    """Build and compile the complete stateful assessment workflow graph."""
    builder = StateGraph(AssessmentState)
    
    # Register Nodes
    builder.add_node("initialize", node_initialize)
    builder.add_node("validate_url", node_validate_url)
    builder.add_node("acquire_repository", node_acquire_repository)
    builder.add_node("analyze_source_code", node_analyze_source_code)
    builder.add_node("index_repository_rag", node_index_repository_rag)
    builder.add_node("retrieve_skill_evidence_rag", node_retrieve_skill_evidence_rag)
    builder.add_node("plan_investigation", node_plan_investigation)
    builder.add_node("execute_investigation", node_execute_investigation)
    builder.add_node("reflect_and_replan", node_reflect_and_replan)
    builder.add_node("evaluate_skills", node_evaluate_skills)
    builder.add_node("generate_viva", node_generate_viva)
    builder.add_node("finalize_assessment", node_finalize_assessment)
    
    # Linear Pre-Investigation Chain
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "validate_url")
    builder.add_edge("validate_url", "acquire_repository")
    builder.add_edge("acquire_repository", "analyze_source_code")
    builder.add_edge("analyze_source_code", "index_repository_rag")
    builder.add_edge("index_repository_rag", "retrieve_skill_evidence_rag")
    builder.add_edge("retrieve_skill_evidence_rag", "plan_investigation")
    builder.add_edge("plan_investigation", "execute_investigation")
    builder.add_edge("execute_investigation", "reflect_and_replan")
    
    # Conditional Replanning Loop
    builder.add_conditional_edges(
        "reflect_and_replan",
        route_investigation,
        {
            "execute_investigation": "execute_investigation",
            "evaluate_skills": "evaluate_skills"
        }
    )
    
    # Post-Investigation Evaluation Chain
    builder.add_edge("evaluate_skills", "generate_viva")
    builder.add_edge("generate_viva", "finalize_assessment")
    builder.add_edge("finalize_assessment", END)
    
    return builder.compile(checkpointer=checkpointer)

_checkpointer_conn = None
_checkpointer = None

def get_checkpointer() -> SqliteSaver:
    global _checkpointer_conn, _checkpointer
    if _checkpointer is None:
        _checkpointer_conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _checkpointer = SqliteSaver(_checkpointer_conn)
        _checkpointer.setup()
    return _checkpointer

_compiled_graph = None

def get_assessment_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_assessment_graph(checkpointer=get_checkpointer())
    return _compiled_graph
