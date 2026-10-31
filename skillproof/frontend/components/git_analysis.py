import streamlit as st
import plotly.graph_objects as go
from services.session_manager import SessionManager


def render_git_forensics():
    """Render Git Forensics dashboard with dynamic Plotly charts and commit cadence analysis."""
    session = SessionManager.get_session()
    commits = session.get("git_commits", [])
    cand_id = session.get("selected_candidate_id") or session.get("candidate_id", "")
    repo_url = session.get("selected_repository_url") or session.get("repo_url", "")

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                Git Forensics & Provenance Audit
            </h1>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                Historical commit cadence analysis, diff size distribution, and file introduction chronology.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Policy Notice
    st.markdown(
        """
        <div style="background: rgba(37, 99, 235, 0.1); border-left: 4px solid #2563EB; border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 20px;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">
                ⚖️ FORENSIC AUDITING PRINCIPLE
            </div>
            <div style="font-size: 0.85rem; color: #F8FAFC; line-height: 1.4; margin-top: 2px;">
                Observable commit logs and timestamps document engineering progression. 
                <em>Note: Git author metadata establishes commit history but does not independently prove biological personal authorship without technical viva verification.</em>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not commits:
        st.info("No git commit forensics available. Commit history will be inspected during backend repository verification.")
        return

    # Plotly Charts: Commit Size & Diff Distribution
    c_chart1, c_chart2 = st.columns([1.2, 1])

    with c_chart1:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <h4 style="margin: 0 0 10px 0; color: #F8FAFC; font-size: 1rem;">Commit Code Diff Distribution</h4>
            """,
            unsafe_allow_html=True,
        )
        dates = [c.get("date", "")[:10] for c in commits]
        insertions = [c.get("insertions", 0) for c in commits]
        deletions = [c.get("deletions", 0) for c in commits]

        fig_diff = go.Figure()
        fig_diff.add_trace(go.Bar(
            name="Lines Added (+)",
            x=dates,
            y=insertions,
            marker_color="#22C55E"
        ))
        fig_diff.add_trace(go.Bar(
            name="Lines Removed (-)",
            x=dates,
            y=deletions,
            marker_color="#EF4444"
        ))
        fig_diff.update_layout(
            barmode='group',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            height=250,
            xaxis=dict(gridcolor="#334155", tickfont=dict(color="#CBD5E1")),
            yaxis=dict(gridcolor="#334155", tickfont=dict(color="#CBD5E1")),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#F8FAFC", size=10)
            )
        )
        st.plotly_chart(fig_diff, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_chart2:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <h4 style="margin: 0 0 10px 0; color: #F8FAFC; font-size: 1rem;">Cumulative Commit Growth</h4>
            """,
            unsafe_allow_html=True,
        )
        commit_indices = [f"#{i+1}" for i in range(len(commits))]
        cum_files = []
        running_sum = 0
        for c in commits:
            running_sum += c.get("files_changed", 1)
            cum_files.append(running_sum)

        fig_prog = go.Figure(data=[go.Scatter(
            x=commit_indices,
            y=cum_files,
            mode='lines+markers',
            line=dict(color='#2563EB', width=3),
            marker=dict(size=8, color='#2563EB')
        )])
        fig_prog.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            height=250,
            xaxis=dict(gridcolor="#334155", tickfont=dict(color="#CBD5E1", size=9)),
            yaxis=dict(gridcolor="#334155", tickfont=dict(color="#CBD5E1"), title=dict(text="Total Files Touched", font=dict(color="#CBD5E1", size=10)))
        )
        st.plotly_chart(fig_prog, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Commit History Ledger Table
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px;">
            <h4 style="margin: 0 0 14px 0; color: #F8FAFC; font-size: 1.05rem;">Chronological Commit Audit Log</h4>
        """,
        unsafe_allow_html=True,
    )

    for c in commits:
        st.markdown(
            f"""
            <div style="border-bottom: 1px solid #334155; padding: 10px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <code style="background: #101827; color: #22C55E; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">{c.get('hash', '')[:8]}</code>
                        <span style="font-weight: 700; color: #F8FAFC; margin-left: 8px;">{c.get('message', '')}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">{c.get('date', '')}</div>
                </div>
                <div style="font-size: 0.78rem; color: #CBD5E1; margin-top: 4px;">
                    Author: <span style="color: #F8FAFC;">{c.get('author', 'Unknown')}</span> |
                    <span style="color: #22C55E;">+{c.get('insertions', 0)} lines</span> /
                    <span style="color: #EF4444;">-{c.get('deletions', 0)} lines</span> ({c.get('files_changed', 0)} files changed)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
