import streamlit as st
from config import DEFAULT_BACKEND_URL
from services.api_client import APIClient
from services.session_manager import SessionManager


def render_technical_viva():
    """Render interactive technical viva interview suite with multi-dimensional grading and zero synthetic data."""
    session = SessionManager.get_session()
    cand_id = session.get("selected_candidate_id") or session.get("candidate_id", "")
    session_id = session.get("session_id", "")
    viva_questions = session.get("viva_questions", [])

    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    api_client = APIClient(base_url=backend_url, timeout=5)
    is_live = st.session_state.get("backend_connected", False)

    # Header
    st.markdown(
        f"""
        <div style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                        Interactive Technical Viva Interview
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                        Targeted architectural inquiries synthesized from candidate's verified source code {f'({cand_id})' if cand_id else ''}.
                    </p>
                </div>
                <div>
                    {'<span class="badge-verified">LIVE FASTAPI INTERVIEW API</span>' if is_live else '<span class="badge-pending">BACKEND OFFLINE</span>'}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not viva_questions:
        st.info("No technical viva inquiries currently available. Once repository analysis is conducted, the verification engine synthesizes targeted conceptual inquiries for candidate evaluation.")
        return

    # Questions Loop
    for idx, q_data in enumerate(viva_questions):
        qid = q_data.get("id", f"Q{idx+1}")
        q_text = q_data.get("question", "")
        diff = q_data.get("difficulty", "Advanced")
        src = q_data.get("source_file", "")
        func = q_data.get("function", "")
        ctx = q_data.get("context", "")
        concepts = q_data.get("expected_concepts", [])

        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="background: rgba(37, 99, 235, 0.2); color: #F8FAFC; font-weight: 800; font-size: 0.75rem; padding: 3px 8px; border-radius: 4px; border: 1px solid #2563EB;">
                            QUESTION {idx + 1} ({qid})
                        </span>
                        <span style="background: rgba(34, 197, 94, 0.15); color: #22C55E; font-size: 0.72rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;">
                            {diff}
                        </span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">
                        Target: <code style="color: #2563EB;">{src}</code> • <code style="color: #F8FAFC;">{func}</code>
                    </div>
                </div>

                <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; line-height: 1.4; margin-bottom: 12px;">
                    {q_text}
                </div>

                <div style="font-size: 0.78rem; color: #CBD5E1; background: #101827; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px;">
                    <strong>Implementation Context:</strong> {ctx}
                </div>

                <div style="font-size: 0.75rem; color: #94A3B8; margin-bottom: 10px;">
                    <strong>Expected Technical Concepts:</strong> {' '.join([f'<code style="color: #CBD5E1; background: #101827; padding: 1px 5px; border-radius: 3px; margin: 1px;">{c}</code>' for c in concepts])}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ans_key = f"viva_ans_{qid}"
        user_answer = st.text_area(
            f"Candidate Response for {qid}:",
            value=st.session_state.get(ans_key, ""),
            key=f"input_{ans_key}",
            height=90,
            placeholder="Articulate theoretical rationale, equation mechanics, and architectural tradeoffs...",
        )

        sub_ans = st.button(f"📤 Submit Answer ({qid})", key=f"btn_sub_{qid}", type="primary")

        eval_key = f"eval_res_{qid}"
        if sub_ans and user_answer.strip():
            if is_live:
                ok, live_eval, err = api_client.submit_viva_answer(session_id, qid, user_answer)
                if ok:
                    st.session_state[eval_key] = live_eval
                else:
                    st.error(f"Viva submission error: {err}")
            else:
                st.warning("Backend service is offline. Live FastAPI backend connection is required to evaluate technical viva responses.")

        active_eval = st.session_state.get(eval_key)

        if active_eval:
            tc = active_eval.get("technical_correctness", 0)
            un = active_eval.get("understanding", 0)
            re = active_eval.get("reasoning", 0)
            ea = active_eval.get("evidence_alignment", 0)
            la = active_eval.get("limitations_awareness", 0)
            ov = active_eval.get("overall_score", 0)
            fb = active_eval.get("feedback", "")
            fu = active_eval.get("follow_up", "")

            st.markdown(
                f"""
                <div style="background: #101827; border: 1px solid #22C55E; border-radius: 10px; padding: 16px; margin: 8px 0 24px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="font-weight: 800; color: #22C55E; font-size: 0.95rem;">
                            🎯 EVALUATION SCORE: {ov}/100
                        </span>
                        <span style="font-size: 0.72rem; color: #94A3B8;">Multi-dimensional grading rubric</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.caption(f"Correctness: {tc}%")
                st.progress(tc / 100)
            with m2:
                st.caption(f"Understanding: {un}%")
                st.progress(un / 100)
            with m3:
                st.caption(f"Reasoning: {re}%")
                st.progress(re / 100)
            with m4:
                st.caption(f"Evidence Align: {ea}%")
                st.progress(ea / 100)
            with m5:
                st.caption(f"Limitations: {la}%")
                st.progress(la / 100)

            st.markdown(
                f"""
                    <div style="margin-top: 12px; font-size: 0.85rem; color: #F8FAFC; background: rgba(34, 197, 94, 0.08); padding: 10px; border-radius: 6px;">
                        <strong>Auditor Feedback:</strong> {fb}
                    </div>
                    {f'<div style="margin-top: 6px; font-size: 0.82rem; color: #2563EB;"><strong>Follow-up Inquiry:</strong> {fu}</div>' if fu else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Next Step
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        if st.button("⬅️ Back to Skill Assessment", use_container_width=True):
            st.session_state["current_page"] = "Skill Assessment"
            st.rerun()
    with col_n2:
        if st.button("👤 Proceed to Human Reviewer Approval →", type="primary", use_container_width=True):
            st.session_state["current_page"] = "Reviewer Approval"
            st.rerun()
