import streamlit as st
from config import EVIDENCE_CLASSIFICATIONS, SUPPORTED_SKILLS
from services.session_manager import SessionManager

CLASSIFICATION_COLORS = {
    "IMPLEMENTED": "#22C55E",
    "TESTED": "#2563EB",
    "PARTIALLY_IMPLEMENTED": "#F59E0B",
    "PLANNED": "#60A5FA",
    "UNVERIFIED": "#94A3B8",
    "NOT_DEMONSTRATED": "#EF4444",
}


def render_evidence_explorer():
    """Render the Evidence Explorer with filtering by skill and classification."""
    session = SessionManager.get_session()
    cand_id = session.get("candidate_id") or st.session_state.get("selected_candidate_id", "")
    evidence_list = session.get("code_evidence", []) or session.get("evidence", []) or session.get("evidence_cards", [])
    repo_url = session.get("selected_repository_url") or session.get("repo_url", "")

    if not evidence_list:
        active_sid = st.session_state.get("active_session_id")
        from services.api_client import APIClient
        from config import DEFAULT_BACKEND_URL
        api_client = APIClient(base_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL), timeout=5)

        if active_sid:
            ok, s_data, _ = api_client.get_session(active_sid)
            if ok and s_data:
                SessionManager.set_session(s_data)
                evidence_list = s_data.get("code_evidence", []) or s_data.get("evidence", [])

        if not evidence_list:
            st.markdown(
                """
                <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 40px 20px; text-align: center;">
                    <div style="font-size: 2rem; margin-bottom: 10px;">📋</div>
                    <h3 style="color: #F8FAFC; margin-bottom: 6px;">No Skill Evidence Available Yet</h3>
                    <p style="color: #94A3B8; font-size: 0.9rem; max-width: 500px; margin: 0 auto;">
                        Skill evidence cards mapping source code implementations to AST line ranges and tests appear when analysis executes.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if repo_url and st.button("🚀 Extract AST Code Evidence Now", key="btn_extract_evidence_now"):
                with st.spinner("Extracting AST findings & syntax evidence..."):
                    ok, res, _ = api_client.start_analysis(
                        candidate_id=cand_id or "CANDIDATE",
                        repo_url=repo_url,
                        claimed_skills=["Python", "Software Architecture"],
                    )
                    if ok and res.get("session_id"):
                        st.session_state["active_session_id"] = res["session_id"]
                        st.rerun()
            return

    # Filters Row
    f_col1, f_col2 = st.columns([1, 1])
    with f_col1:
        skills_claimed = list(set([c.get("skill", "") for c in evidence_list if c.get("skill")]))
        selected_skill = st.selectbox(
            "Filter by Skill Claim",
            options=["ALL SKILLS"] + (skills_claimed if skills_claimed else SUPPORTED_SKILLS),
        )
    with f_col2:
        selected_class = st.selectbox(
            "Filter by Evidence Classification",
            options=["ALL CLASSIFICATIONS"] + EVIDENCE_CLASSIFICATIONS,
        )

    filtered = evidence_list
    if selected_skill != "ALL SKILLS":
        filtered = [c for c in filtered if c.get("skill") == selected_skill]
    if selected_class != "ALL CLASSIFICATIONS":
        filtered = [c for c in filtered if c.get("classification") == selected_class]

    st.markdown(f"<div style='font-size: 0.85rem; color: #CBD5E1; margin: 12px 0;'>Showing <strong>{len(filtered)}</strong> evidence records:</div>", unsafe_allow_html=True)

    for item in filtered:
        card_id = item.get("id", "EVID-00")
        skill = item.get("skill", "General")
        cls = item.get("classification", "UNVERIFIED")
        color = CLASSIFICATION_COLORS.get(cls, "#2563EB")
        file_path = item.get("file_path", "")
        line_range = item.get("line_range", "")
        target = item.get("target", "")
        explanation = item.get("explanation", "")
        test_ref = item.get("test_reference", "")
        test_res = item.get("test_result", "")
        strength = item.get("evidence_strength", "Medium")
        limitations = item.get("limitations", "None noted.")
        snippet = item.get("snippet", "")

        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 18px 20px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 0.75rem; font-weight: 700; color: #94A3B8; font-family: monospace;">{card_id}</span>
                        <strong style="color: #F8FAFC; font-size: 1.05rem;">{skill}</strong>
                    </div>
                    <span style="background: rgba(37, 99, 235, 0.15); color: {color}; border: 1px solid {color}; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700;">
                        {cls}
                    </span>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; background: #0B1220; border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 12px; font-size: 0.8rem;">
                    <div>
                        <span style="color: #94A3B8;">Target Symbol:</span>
                        <div style="font-family: monospace; font-weight: 700; color: #60A5FA;">{target}</div>
                    </div>
                    <div>
                        <span style="color: #94A3B8;">File Location:</span>
                        <div style="font-family: monospace; color: #CBD5E1;">{file_path} {line_range}</div>
                    </div>
                    <div>
                        <span style="color: #94A3B8;">Evidence Strength:</span>
                        <div style="font-weight: 700; color: #22C55E;">{strength}</div>
                    </div>
                </div>

                <p style="color: #CBD5E1; font-size: 0.88rem; line-height: 1.5; margin: 0 0 10px 0;">
                    {explanation}
                </p>

                {f'''
                <div style="border-top: 1px solid #334155; padding-top: 8px; margin-top: 8px; font-size: 0.8rem; color: #94A3B8;">
                    <strong>Pytest Reference:</strong> <code>{test_ref}</code> | <span style="color: #22C55E;">{test_res}</span>
                </div>
                ''' if test_ref else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if snippet:
            with st.expander(f"View Code Evidence ({card_id})", expanded=False):
                st.code(snippet, language="python")
