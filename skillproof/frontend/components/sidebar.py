import streamlit as st
from config import APP_ICON, APP_NAME, APP_TAGLINE, DEFAULT_BACKEND_URL, NAVIGATION_PAGES
from services.api_client import APIClient
from services.session_manager import SessionManager


def render_sidebar() -> str:
    """Render consistent enterprise sidebar with branding, navigation, and connection telemetry."""
    with st.sidebar:
        # Branding
        st.markdown(
            f"""
            <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #334155; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 2rem;">{APP_ICON}</span>
                    <div>
                        <h2 style="margin: 0; font-size: 1.35rem; color: #F8FAFC; font-weight: 800; letter-spacing: -0.5px;">{APP_NAME}</h2>
                        <span style="font-size: 0.7rem; color: #60A5FA; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">SKILL VERIFICATION</span>
                    </div>
                </div>
                <p style="margin: 6px 0 0 0; font-size: 0.78rem; color: #CBD5E1; line-height: 1.3;">
                    {APP_TAGLINE}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Dynamic Candidate & Repository Status Card
        session = SessionManager.get_session()
        cand_id = session.get("candidate_id") or st.session_state.get("selected_candidate_id", "")
        repo_url = session.get("repo_url") or st.session_state.get("selected_repository_url", "") or st.session_state.get("selected_repo_url", "")
        repo_name = session.get("repo_info", {}).get("repo_name", "") or st.session_state.get("selected_repository_name", "")
        if not repo_name and repo_url:
            repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        parsed_profile = st.session_state.get("parsed_resume_profile") or session.get("resume_info") or {}
        cand_name = parsed_profile.get("candidate_name")
        resume_name = st.session_state.get("uploaded_resume_name") or parsed_profile.get("filename")
        resume_skills_count = len(st.session_state.get("resume_extracted_skills", []) or parsed_profile.get("extracted_skills", []))

        is_prepared = bool(cand_id and repo_url)

        if is_prepared:
            display_title = f"{cand_name} ({cand_id})" if cand_name else cand_id
            resume_badge = f'<div style="font-size: 0.72rem; color: #22C55E; margin-top: 4px;">📄 Resume: {resume_name or "Parsed"} ({resume_skills_count} skills)</div>' if (resume_name or resume_skills_count) else '<div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">📄 No resume attached</div>'
            st.markdown(
                f"""
                <div style="background: #1B2638; border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.68rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">ACTIVE CANDIDATE</span>
                        <span class="badge-verified" style="font-size: 0.65rem; padding: 2px 8px;">PREPARED</span>
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 800; color: #F8FAFC; margin-top: 4px;">{display_title}</div>
                    <div style="font-size: 0.78rem; color: #60A5FA; margin-top: 2px; word-break: break-all;">
                        🔗 {repo_name or repo_url}
                    </div>
                    {resume_badge}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: #1B2638; border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.68rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">CANDIDATE SELECTION</span>
                        <span class="badge-pending" style="font-size: 0.65rem; padding: 2px 8px;">AWAITING INPUT</span>
                    </div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #F8FAFC; margin-top: 4px;">No Candidate Selected</div>
                    <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 2px;">
                        Paste repo URL & upload resume on Overview
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Navigation Pages (Preserve all 12 navigation items)
        labels = [p[0] for p in NAVIGATION_PAGES]
        keys = [p[1] for p in NAVIGATION_PAGES]

        curr_page = st.session_state.get("current_page", "Overview")
        curr_idx = keys.index(curr_page) if curr_page in keys else 0

        selected_label = st.radio(
            "Navigation",
            labels,
            index=curr_idx,
            label_visibility="collapsed",
        )
        selected_key = keys[labels.index(selected_label)]
        st.session_state["current_page"] = selected_key

        st.markdown("<hr style='border-color: #334155; margin: 16px 0;'>", unsafe_allow_html=True)

        # Backend Health & Connection Telemetry (Genuine checks only)
        backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
        api_client = APIClient(base_url=backend_url, timeout=2)
        is_live, health_msg = api_client.check_health()
        st.session_state["backend_connected"] = is_live

        if is_live:
            st.markdown(
                f"""
                <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid #22C55E; border-radius: 8px; padding: 10px; margin-bottom: 12px;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #22C55E; display: flex; align-items: center; gap: 6px;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: #22C55E;"></span>
                        FASTAPI BACKEND ONLINE
                    </div>
                    <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 2px; font-family: monospace;">{backend_url}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid #F59E0B; border-radius: 8px; padding: 10px; margin-bottom: 12px;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #F59E0B; display: flex; align-items: center; gap: 6px;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: #F59E0B;"></span>
                        BACKEND OFFLINE
                    </div>
                    <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 2px;">
                        Backend at {backend_url} offline. Staging verification parameters locally.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Configuration Expander
        with st.expander("⚙️ Session & Backend Settings", expanded=False):
            new_url = st.text_input("Backend IP / Port", value=backend_url, help="Set backend address, e.g. http://127.0.0.1:8001")
            if new_url != backend_url:
                st.session_state["backend_url"] = new_url
                st.rerun()
            st.caption("Default: http://127.0.0.1:8001")

            if st.button("Clear Candidate Selection", use_container_width=True):
                SessionManager.clear_session()
                st.rerun()

        # Footer
        st.markdown(
            """
            <div style="font-size: 0.68rem; color: #94A3B8; text-align: center; margin-top: 20px;">
                SkillProof AI • Skill-Proof Verifier Agent
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["current_page"]
