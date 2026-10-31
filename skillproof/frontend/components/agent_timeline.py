import streamlit as st
from services.session_manager import SessionManager

STAGE_COLORS = {
    "PLAN": "#2563EB",
    "ACT": "#22C55E",
    "OBSERVE": "#2563EB",
    "CRITIQUE": "#F59E0B",
    "REPLANNING": "#EF4444",
    "RE-PLAN": "#EF4444",
    "ACT AGAIN": "#22C55E",
    "VERIFY": "#22C55E",
}

STATUS_BADGES = {
    "COMPLETED": "badge-verified",
    "PREPARED": "badge-verified",
    "REPLANNING": "badge-pending",
    "WAITING_FOR_APPROVAL": "badge-pending",
    "RUNNING": "badge-pending",
    "IN_PROGRESS": "badge-pending",
    "FAILED": "badge-rejected",
    "PENDING": "badge-pending",
}


def render_agent_workspace_timeline():
    """Render the central Agent Workspace showing real-time agent choreography and re-planning."""
    session = SessionManager.get_session()
    cand_id = session.get("selected_candidate_id") or session.get("candidate_id", "")
    repo_url = session.get("selected_repository_url") or session.get("repo_url", "")
    session_id = session.get("session_id", "")
    actual_status = (session.get("status") or ("PREPARED" if cand_id else "NO_SELECTION")).upper()
    timeline = session.get("timeline", [])

    display_cand = cand_id if cand_id else "None Selected"
    display_repo = repo_url if repo_url else "None Selected"

    # Top Header
    st.markdown(
        f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                        Autonomous Agent Workspace
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                        Real-time choreography: Plan → Act → Observe → Critique → Re-Plan → Act Again → Verify.
                    </p>
                </div>
                <div>
                    <span class="badge-verified">ACTIVE AGENT SWARM • CANDIDATE {display_cand}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Actual Verification Status Strip
    status_badge_class = STATUS_BADGES.get(actual_status, "badge-pending")
    st.markdown(
        f"""
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">ACTIVE VERIFICATION SESSION</div>
                <div style="display: flex; align-items: center; gap: 10px; margin-top: 4px; flex-wrap: wrap;">
                    <code style="background: #101827; color: #22C55E; padding: 3px 8px; border-radius: 6px; font-size: 0.88rem; border: 1px solid #334155;">{session_id if session_id else "unassigned"}</code>
                    <span style="color: #64748B;">•</span>
                    <span style="color: #F8FAFC; font-weight: 700; font-size: 0.85rem;">Candidate: {display_cand}</span>
                    <span style="color: #64748B;">•</span>
                    <a href="{repo_url if repo_url.startswith('https://') else '#'}" target="_blank" style="color: #2563EB; font-size: 0.85rem; text-decoration: underline; font-weight: 600;">🔗 {display_repo}</a>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="text-align: right;">
                    <span style="font-size: 0.68rem; color: #94A3B8; text-transform: uppercase; font-weight: 700; display: block;">VERIFICATION STATUS</span>
                    <span class="{status_badge_class}" style="font-size: 0.82rem; font-weight: 800; padding: 4px 12px; display: inline-block; margin-top: 2px;">
                        ● {actual_status}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Core Execution Loop Banner
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px 20px; margin-bottom: 24px;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #2563EB; text-transform: uppercase; margin-bottom: 10px;">
                AUTONOMOUS REASONING & RE-PLANNING DAG SEQUENCE
            </div>
            <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 0.8rem; font-weight: 700;">
                <span style="background: rgba(37, 99, 235, 0.15); color: #F8FAFC; border: 1px solid #2563EB; padding: 4px 10px; border-radius: 6px;">1. PLAN</span>
                <span style="color: #64748B;">→</span>
                <span style="background: rgba(34, 197, 94, 0.15); color: #22C55E; border: 1px solid #22C55E; padding: 4px 10px; border-radius: 6px;">2. ACT</span>
                <span style="color: #64748B;">→</span>
                <span style="background: rgba(37, 99, 235, 0.15); color: #F8FAFC; border: 1px solid #2563EB; padding: 4px 10px; border-radius: 6px;">3. OBSERVE</span>
                <span style="color: #64748B;">→</span>
                <span style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; padding: 4px 10px; border-radius: 6px;">4. CRITIQUE</span>
                <span style="color: #64748B;">→</span>
                <span style="background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; padding: 4px 10px; border-radius: 6px;">5. RE-PLAN</span>
                <span style="color: #64748B;">→</span>
                <span style="background: rgba(34, 197, 94, 0.15); color: #22C55E; border: 1px solid #22C55E; padding: 4px 10px; border-radius: 6px;">6. ACT AGAIN</span>
                <span style="color: #64748B;">→</span>
                <span style="background: rgba(34, 197, 94, 0.15); color: #22C55E; border: 1px solid #22C55E; padding: 4px 10px; border-radius: 6px;">7. VERIFY</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not timeline:
        if cand_id and repo_url:
            st.info(f"Verification parameters prepared for candidate **{cand_id}** on **{repo_url}** (Status: {actual_status}). Awaiting backend agent execution dispatch.")
        else:
            st.info("No candidate repository currently prepared. Please navigate to the **Overview** page and enter a candidate ID and GitHub repository URL.")
            if st.button("← Go to Overview", type="primary"):
                st.session_state["current_page"] = "Overview"
                st.rerun()
        return

    # Render Chronological Agent Execution Steps
    for idx, item in enumerate(timeline):
        agent_name = item.get("agent", "Agent")
        stage = item.get("stage", "ACT")
        objective = item.get("objective", "")
        status = item.get("status", "COMPLETED")
        tool = item.get("tool", "internal")
        obs = item.get("observation", "")
        out = item.get("output", "")
        tm = item.get("timestamp", "00:00:00")

        stage_color = STAGE_COLORS.get(stage, "#2563EB")
        badge_class = STATUS_BADGES.get(status, "badge-verified")

        st.markdown(
            f"""
            <div style="background: #1B2638; border-left: 4px solid {stage_color}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; border-radius: 0 12px 12px 0; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.1rem; font-weight: 800; color: #F8FAFC;">{agent_name}</span>
                        <span style="background: rgba(255,255,255,0.06); color: {stage_color}; border: 1px solid {stage_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800;">
                            STAGE: {stage}
                        </span>
                        <span class="{badge_class}">{status}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8; font-family: monospace;">
                        ⏱️ {tm}
                    </div>
                </div>

                <div style="font-size: 0.85rem; color: #F8FAFC; margin-bottom: 8px;">
                    <strong>Objective:</strong> {objective}
                </div>

                <div style="margin-bottom: 10px;">
                    <span style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">TOOL INVOKED:</span>
                    <code style="background: #101827; color: #2563EB; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 6px; border: 1px solid #334155;">{tool}</code>
                </div>

                <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #22C55E; text-transform: uppercase; margin-bottom: 4px;">OBSERVATION</div>
                    <div style="font-size: 0.82rem; color: #F8FAFC; line-height: 1.4;">{obs}</div>
                </div>

                <div style="font-size: 0.82rem; color: #CBD5E1;">
                    <strong style="color: #22C55E;">OUTPUT / FINDINGS:</strong> {out}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Navigation CTA
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧠 Inspect Repository Intelligence →", type="primary", use_container_width=True):
            st.session_state["current_page"] = "Repository Intelligence"
            st.rerun()
    with c2:
        if st.button("🔎 Explore Skill Evidence Cards →", use_container_width=True):
            st.session_state["current_page"] = "Evidence Explorer"
            st.rerun()
