import streamlit as st
from config import DEFAULT_BACKEND_URL
from services.api_client import APIClient
from services.session_manager import SessionManager


def render_reviewer_approval_console():
    """Render the official Reviewer Approval Console enforcing mandatory human-in-the-loop audit sign-off with zero synthetic data."""
    session = SessionManager.get_session()
    cand_id = session.get("selected_candidate_id") or session.get("candidate_id", "")
    session_id = session.get("session_id", "")
    approval = session.get("approval", {})
    status = session.get("approval_status", "pending")

    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    api_client = APIClient(base_url=backend_url, timeout=5)
    is_live = st.session_state.get("backend_connected", False)

    # Top Status Banner
    if status == "approved":
        st.markdown(
            f"""
            <div style="background: rgba(34, 197, 94, 0.12); border: 2px solid #22C55E; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #22C55E; margin-bottom: 4px;">
                    ✅ CANDIDATE STATUS: OFFICIALLY APPROVED
                </div>
                <div style="font-size: 0.9rem; color: #F8FAFC;">
                    Audited and approved by <strong>{approval.get('reviewer_id', 'Auditor')}</strong> at {approval.get('timestamp', 'recently')}. Credential issuance unlocked.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif status == "rejected":
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.12); border: 2px solid #EF4444; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #EF4444; margin-bottom: 4px;">
                    ❌ CANDIDATE STATUS: REJECTED BY AUDITOR
                </div>
                <div style="font-size: 0.9rem; color: #F8FAFC;">
                    Reason: {approval.get('reviewer_notes', 'Evidence insufficient or contradictory viva.')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background: rgba(245, 158, 11, 0.12); border: 2px solid #F59E0B; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #F59E0B; margin-bottom: 4px;">
                    ⏳ CANDIDATE STATUS: PENDING HUMAN AUDITOR APPROVAL
                </div>
                <div style="font-size: 0.9rem; color: #F8FAFC;">
                    Mandatory Policy Rule: Autonomous agents never auto-approve candidates without explicit human auditor sign-off.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Check if dossier evidence exists
    assessment = session.get("skill_assessment", {})
    overall_score = assessment.get("overall_score")
    claimed_skills = session.get("selected_claimed_skills") or session.get("claimed_skills", [])
    commits = session.get("git_commits", [])
    test_data = session.get("test_results", {})
    viva_questions = session.get("viva_questions", [])

    if not cand_id and overall_score is None and not commits:
        st.info("No verification dossier available for review. Verification results will appear here once candidate repository analysis is completed.")
        return

    # Dynamic Dossier Summary
    display_score = f"{overall_score} / 100" if overall_score is not None else "Pending Verification"
    commits_str = f"{len(commits)} commits inspected" if commits else "No commit data"
    tests_str = f"{test_data.get('passed', 0)} of {test_data.get('total', 0)} passed" if test_data.get("cases") else "Pending harness"
    viva_evals = [q.get("evaluation", {}).get("overall_score", 0) for q in viva_questions if "evaluation" in q]
    viva_str = f"{sum(viva_evals) / len(viva_evals):.1f} / 100" if viva_evals else "Awaiting viva"

    st.markdown(
        f"""
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <h3 style="margin: 0 0 16px 0; color: #F8FAFC; font-size: 1.2rem; font-weight: 700;">
                Comprehensive Audit Dossier for {cand_id if cand_id else 'Candidate'}
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 16px;">
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Claimed Skills</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC;">{', '.join(claimed_skills) if claimed_skills else 'None specified'}</div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Overall Evidence Score</span>
                    <div style="font-size: 1.2rem; font-weight: 800; color: #22C55E;">{display_score}</div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Pytest Verification</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #2563EB;">{tests_str}</div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Git Cadence Provenance</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC;">{commits_str}</div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Viva Technical Average</span>
                    <div style="font-size: 1.2rem; font-weight: 800; color: #22C55E;">{viva_str}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Reviewer Action Form
    with st.form("formal_reviewer_form"):
        st.markdown("<h4 style='color: #F8FAFC; margin-bottom: 12px;'>Official Auditor Review Sign-Off</h4>", unsafe_allow_html=True)
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            decision = st.radio(
                "Reviewer Verdict:",
                ["APPROVE CANDIDATE", "REJECT CANDIDATE"],
                index=0 if status != "rejected" else 1,
                horizontal=True,
            )
        with col_r2:
            reviewer_id = st.text_input("Auditor Identity (Badge / ID):", value=approval.get("reviewer_id", ""), placeholder="Enter auditor ID")

        notes = st.text_area("Audit Rationale & Justification (Mandatory):", value=approval.get("reviewer_notes", ""), placeholder="Enter audit rationale and justification...", height=90)

        submit_review = st.form_submit_button("🔒 Record Official Auditor Decision", type="primary", use_container_width=True)

    if submit_review:
        if not notes.strip():
            st.error("Audit rationale is strictly mandatory.")
            return

        api_decision = "approved" if decision == "APPROVE CANDIDATE" else "rejected"

        if is_live:
            ok, resp, err = api_client.submit_approval(session_id, api_decision, notes, reviewer_id)
            if ok:
                st.session_state["active_session"]["approval_status"] = api_decision
                st.session_state["active_session"]["approval"] = {
                    "decision": api_decision,
                    "reviewer_notes": notes,
                    "reviewer_id": reviewer_id,
                }
                st.success("Auditor decision successfully registered in backend!")
                st.rerun()
            else:
                st.error(f"Approval failed: {err}")
        else:
            st.session_state["active_session"]["approval_status"] = api_decision
            st.session_state["active_session"]["approval"] = {
                "decision": api_decision,
                "reviewer_notes": notes,
                "reviewer_id": reviewer_id,
            }
            st.success(f"Reviewer verdict '{api_decision}' successfully recorded for {cand_id}!")
            st.rerun()
