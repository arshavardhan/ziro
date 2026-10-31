import streamlit as st
import plotly.graph_objects as go
from services.session_manager import SessionManager


def render_skill_assessment_dashboard():
    """Render interactive skill assessment dashboard with Plotly radar charts, verdict pills, and dual-axis scores."""
    session = SessionManager.get_session()
    cand_id = session.get("selected_candidate_id") or session.get("candidate_id", "")
    display_cand = cand_id if cand_id else "Unspecified Candidate"
    assessment = session.get("skill_assessment", {})
    skills_data = assessment.get("skills", {}) or session.get("skill_scores", {})
    overall_score = assessment.get("overall_score")
    overall_verdict = assessment.get("verdict", "PENDING_VERIFICATION")
    repo_url = session.get("selected_repository_url") or session.get("repo_url", "")

    if not skills_data:
        active_sid = st.session_state.get("active_session_id")
        from services.api_client import APIClient
        from config import DEFAULT_BACKEND_URL
        api_client = APIClient(base_url=st.session_state.get("backend_url", DEFAULT_BACKEND_URL), timeout=5)

        if active_sid:
            ok, s_data, _ = api_client.get_session(active_sid)
            if ok and s_data:
                SessionManager.set_session(s_data)
                assessment = s_data.get("skill_assessment", {})
                skills_data = assessment.get("skills", {}) or s_data.get("skill_scores", {})
                overall_score = assessment.get("overall_score")
                overall_verdict = assessment.get("verdict", "VERIFIED")

        if not skills_data:
            st.info("No skill assessment results available yet for this candidate.")
            if repo_url and st.button("🚀 Evaluate Candidate Skills Now", key="btn_eval_skills_now"):
                with st.spinner("Analyzing code evidence & scoring skills..."):
                    ok, res, _ = api_client.start_analysis(
                        candidate_id=cand_id or "CANDIDATE",
                        repo_url=repo_url,
                        claimed_skills=["Python", "Software Architecture", "Git/GitHub"],
                    )
                    if ok and res.get("session_id"):
                        st.session_state["active_session_id"] = res["session_id"]
                        st.rerun()
            return

    # Plotly Charts: Radar + Breakdown
    c_radar, c_bars = st.columns([1, 1.2])

    with c_radar:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <h4 style="margin: 0 0 10px 0; color: #F8FAFC; font-size: 1rem;">Skill Radar Assessment</h4>
            """,
            unsafe_allow_html=True,
        )
        cat_names = list(skills_data.keys())
        impl_scores = [skills_data[k].get("impl_score", 0) for k in cat_names]
        viva_scores = [skills_data[k].get("viva_score", 0) for k in cat_names]

        # Close loop
        cats_closed = cat_names + [cat_names[0]]
        impl_closed = impl_scores + [impl_scores[0]]
        viva_closed = viva_scores + [viva_scores[0]]

        fig_rad = go.Figure()
        fig_rad.add_trace(go.Scatterpolar(
            r=impl_closed,
            theta=cats_closed,
            fill='toself',
            fillcolor='rgba(37, 99, 235, 0.25)',
            line=dict(color='#2563EB', width=2),
            name='Code Implementation Score'
        ))
        fig_rad.add_trace(go.Scatterpolar(
            r=viva_closed,
            theta=cats_closed,
            fill='toself',
            fillcolor='rgba(34, 197, 94, 0.2)',
            line=dict(color='#22C55E', width=2, dash='dot'),
            name='Candidate Viva Score'
        ))
        fig_rad.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#334155", tickfont=dict(color="#CBD5E1", size=9)),
                angularaxis=dict(gridcolor="#334155", tickfont=dict(color="#F8FAFC", size=10)),
                bgcolor="rgba(11, 18, 32, 0.6)"
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=9))
        )
        st.plotly_chart(fig_rad, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_bars:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <h4 style="margin: 0 0 10px 0; color: #F8FAFC; font-size: 1rem;">Evidence Coverage & Test Scores</h4>
            """,
            unsafe_allow_html=True,
        )
        cov_scores = [skills_data[k].get("coverage", 0) for k in cat_names]
        test_scores = [skills_data[k].get("test_score", 0) for k in cat_names]

        fig_cov = go.Figure()
        fig_cov.add_trace(go.Bar(
            name="Implementation Coverage %",
            y=cat_names,
            x=cov_scores,
            orientation='h',
            marker_color="#2563EB"
        ))
        fig_cov.add_trace(go.Bar(
            name="Pytest Verification Score",
            y=cat_names,
            x=test_scores,
            orientation='h',
            marker_color="#22C55E"
        ))
        fig_cov.update_layout(
            barmode='group',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            height=300,
            xaxis=dict(range=[0, 105], gridcolor="#334155", tickfont=dict(color="#CBD5E1")),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#F8FAFC", size=10), autorange="reversed"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#F8FAFC", size=9))
        )
        st.plotly_chart(fig_cov, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Detailed Skill Assessment Cards
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px;">
            <h4 style="margin: 0 0 16px 0; color: #F8FAFC; font-size: 1.1rem;">Individual Skill Assessment Breakdown</h4>
        """,
        unsafe_allow_html=True,
    )

    for skill_name, s_info in skills_data.items():
        verdict = s_info.get("verdict", "VERIFIED")
        v_class = "badge-verified" if verdict == "VERIFIED" else ("badge-pending" if verdict == "PARTIALLY_VERIFIED" else "badge-rejected")

        with st.expander(f"**{skill_name}** • Verdict: {verdict} (Implementation: {s_info.get('impl_score', 0)}%, Viva: {s_info.get('viva_score', 0)}%)", expanded=True):
            col_d1, col_d2 = st.columns([1, 1])
            with col_d1:
                st.markdown(f"**Architecture Evidence:** {s_info.get('arch_evidence', 'N/A')}")
                st.markdown(f"**Git Commit Evidence:** {s_info.get('git_evidence', 'N/A')}")
                files_tags = ' '.join([f'<code style="background: #101827; color: #2563EB; font-size: 0.78rem; padding: 2px 6px; border-radius: 4px;">{f}</code>' for f in s_info.get('supporting_files', [])])
                st.markdown(f"**Supporting Files:** {files_tags}", unsafe_allow_html=True)
            with col_d2:
                st.markdown(f"**Identified Limitations:** {s_info.get('limitations', 'None identified')}")
                st.markdown(f"**Missing Evidence:** {s_info.get('missing_evidence', 'None')}")
                st.markdown(f"<span class='{v_class}'>VERDICT: {verdict}</span>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Resume Claims vs Repository Evidence Cross-Verification
    resume_verif = session.get("resume_verification") or {}
    if resume_verif:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #22C55E; border-radius: 12px; padding: 20px; margin-top: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <h4 style="margin: 0; color: #F8FAFC; font-size: 1.1rem;">📄 Resume Claims vs. Repository Code Alignment</h4>
                        <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.85rem;">Cross-verifying claimed skills on resume against real AST findings and code evidence</p>
                    </div>
                    <span class="badge-verified" style="font-size: 0.85rem; padding: 4px 12px;">
                        ALIGNMENT SCORE: {resume_verif.get('alignment_score', 0)}%
                    </span>
                </div>
            """,
            unsafe_allow_html=True,
        )
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("<p style='font-size: 0.82rem; font-weight: 700; color: #22C55E; margin-bottom: 6px;'>✓ DEMONSTRATED IN CODEBASE:</p>", unsafe_allow_html=True)
            for d in resume_verif.get("demonstrated_skills", []):
                st.markdown(f"- **{d['skill']}** `({d.get('evidence_type', 'CODE')})`")
        with col_r2:
            st.markdown("<p style='font-size: 0.82rem; font-weight: 700; color: #F59E0B; margin-bottom: 6px;'>⚠️ UNVERIFIED IN CODEBASE:</p>", unsafe_allow_html=True)
            for u in resume_verif.get("unverified_skills", []):
                st.markdown(f"- **{u['skill']}** — <span style='color: #94A3B8; font-size: 0.8rem;'>{u.get('notes', 'No code evidence')}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
