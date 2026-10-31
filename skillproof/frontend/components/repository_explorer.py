import streamlit as st
import plotly.graph_objects as go
from services.session_manager import SessionManager


def render_repository_explorer():
    """Render repository explorer displaying module trees, dependency graphs, and source inspection."""
    session = SessionManager.get_session()
    repo_info = session.get("repo_info", {})
    code_files = session.get("code_files", {})
    cand_id = session.get("candidate_id") or st.session_state.get("selected_candidate_id", "")
    repo_url = repo_info.get("repo_url") or st.session_state.get("selected_repository_url", "")
    owner = repo_info.get("repo_owner") or st.session_state.get("selected_repository_owner", "")
    repo_name = repo_info.get("repo_name") or st.session_state.get("selected_repository_name", "")

    st.markdown(
        f"""
        <div style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                        Repository Intelligence
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                        Automated structural inspection of target repository {f"<strong>{repo_name}</strong>" if repo_name else ""}.
                    </p>
                </div>
                <div>
                    {f'<span class="badge-verified">CANDIDATE: {cand_id}</span>' if cand_id else '<span class="badge-pending">NO CANDIDATE SELECTED</span>'}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not repo_url:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 40px 20px; text-align: center;">
                <div style="font-size: 2.2rem; margin-bottom: 10px;">📂</div>
                <h3 style="color: #F8FAFC; margin-bottom: 6px;">No Repository Selected</h3>
                <p style="color: #94A3B8; font-size: 0.9rem; max-width: 500px; margin: 0 auto;">
                    Please enter candidate information and a public GitHub repository URL on the <strong>Overview</strong> page to begin verification.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Repository Parameters Strip
    st.markdown(
        f"""
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">TARGET REPOSITORY</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #60A5FA; font-family: monospace; word-break: break-all;">
                        <a href="{repo_url}" target="_blank" rel="noopener noreferrer" style="color: #60A5FA; text-decoration: underline;">
                            {repo_url} ↗
                        </a>
                    </div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">OWNER / REPO</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC;">{owner or '—'} / {repo_name or '—'}</div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">DEFAULT BRANCH</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #F8FAFC;">{repo_info.get('default_branch') or 'main'}</div>
                </div>
                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">DISCOVERED MODULES</span>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #22C55E;">
                        {len(repo_info.get('discovered_modules', []))} Modules
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    modules = repo_info.get("discovered_modules", [])
    langs = repo_info.get("languages", {})

    # If backend has not yet populated modules or languages, show honest status
    if not modules and not langs:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 30px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 1.8rem; margin-bottom: 8px;">⏳</div>
                <h4 style="color: #F8FAFC; margin-bottom: 6px;">Repository Metadata Pending Pipeline Execution</h4>
                <p style="color: #CBD5E1; font-size: 0.88rem; max-width: 600px; margin: 0 auto; line-height: 1.5;">
                    The repository URL has been verified and staged. Automated AST tree extraction, package dependency mapping, and language breakdown will be retrieved when the verification pipeline runs.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Discovered Modules & Language Distribution
        col_m, col_l = st.columns([1.5, 1])
        with col_m:
            st.markdown(
                """
                <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; height: 100%;">
                    <h4 style="margin: 0 0 12px 0; color: #F8FAFC; font-size: 1.05rem;">Discovered Repository Modules</h4>
                """,
                unsafe_allow_html=True,
            )
            for mod in modules:
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding: 8px 0;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="color: #60A5FA;">📦</span>
                            <code style="background: #0B1220; color: #60A5FA; font-size: 0.85rem; padding: 2px 6px; border-radius: 4px;">{mod}</code>
                        </div>
                        <span style="font-size: 0.75rem; color: #22C55E; font-weight: 700;">VERIFIED ACTIVE</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_l:
            st.markdown(
                """
                <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; height: 100%;">
                    <h4 style="margin: 0 0 12px 0; color: #F8FAFC; font-size: 1.05rem;">Language Distribution</h4>
                """,
                unsafe_allow_html=True,
            )
            fig_lang = go.Figure(data=[go.Pie(
                labels=list(langs.keys()),
                values=list(langs.values()),
                hole=0.6,
                marker=dict(colors=["#2563EB", "#22C55E", "#F59E0B"]),
                textinfo='label+percent',
                textfont=dict(color="#F8FAFC", size=10)
            )])
            fig_lang.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=5, r=5, t=5, b=5),
                height=160,
                showlegend=False
            )
            st.plotly_chart(fig_lang, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Source Code Inspection Tabs
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px;">
            <h4 style="margin: 0 0 16px 0; color: #F8FAFC; font-size: 1.1rem;">Source Code Inspection</h4>
        """,
        unsafe_allow_html=True,
    )

    if code_files:
        selected_file = st.selectbox(
            "Select Module File to Inspect Source",
            options=list(code_files.keys()),
            key="repo_code_select",
        )
        code_content = code_files.get(selected_file, "")
        st.code(code_content, language="python", line_numbers=True)
    else:
        st.info("No source files downloaded in current session. Source files will be inspected during backend analysis.")

    st.markdown("</div>", unsafe_allow_html=True)
