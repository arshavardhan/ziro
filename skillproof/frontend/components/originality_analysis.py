import streamlit as st
from services.session_manager import SessionManager


def render_originality_analysis():
    """Render Originality and Code Similarity audit interface with responsible language and zero synthetic data."""
    session = SessionManager.get_session()
    report = session.get("originality_report", {})
    findings = session.get("originality_findings", [])

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                Originality & Code Similarity Audit
            </h1>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                AST fingerprinting and structural pattern inspection against public libraries, tutorials, and common boilerplate.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mandatory Ethical Language Notice
    st.markdown(
        """
        <div style="background: rgba(245, 158, 11, 0.08); border-left: 4px solid #F59E0B; border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 20px;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #F59E0B; text-transform: uppercase;">
                ⚖️ ETHICAL AUDITING POLICY
            </div>
            <div style="font-size: 0.82rem; color: #F8FAFC; line-height: 1.4; margin-top: 2px;">
                Similarity indicators reflect shared mathematical idioms or framework patterns. 
                They are categorized as <strong>"Potential similarity indicators"</strong> to inform human review. 
                In compliance with strict platform policies, automated agents <em>never assert proven plagiarism or AI generation with certainty</em> without independent forensic proof.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not report and not findings:
        st.info("Originality and AST fingerprint analysis has not been executed yet. Prepare or run a verification session to inspect code originality against standard patterns and repositories.")
        return

    # Overall Originality Metric Strip
    c1, c2, c3 = st.columns(3)
    orig_idx = report.get("originality_index", "N/A")
    orig_str = f"{orig_idx}% Original" if isinstance(orig_idx, (int, float)) else str(orig_idx)
    bp_match = report.get("boilerplate_match", "N/A")
    bp_str = f"{bp_match}%" if isinstance(bp_match, (int, float)) else str(bp_match)
    anomaly_sev = report.get("anomaly_severity", "N/A")

    with c1:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Overall Originality Index</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #22C55E; margin: 4px 0;">{orig_str}</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">AST structure comparison</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Boilerplate Pattern Match</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #2563EB; margin: 4px 0;">{bp_str}</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">Standard library idiom matches</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Anomaly Severity</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; margin: 4px 0;">{anomaly_sev}</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">Forensic pattern threshold</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Detailed Findings Table
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px;">
            <h4 style="margin: 0 0 14px 0; color: #F8FAFC; font-size: 1.05rem;">Pattern Analysis & Similarity Findings</h4>
        """,
        unsafe_allow_html=True,
    )

    if not findings:
        st.markdown("<p style='color: #94A3B8; font-size: 0.85rem;'>No similarity anomalies or matching pattern blocks identified in this codebase.</p>", unsafe_allow_html=True)
    else:
        for f in findings:
            st.markdown(
                f"""
                <div style="border-bottom: 1px solid #334155; padding: 12px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div>
                            <span style="font-weight: 700; color: #F8FAFC; font-size: 0.9rem;">{f.get('category', 'Finding')}</span>
                            <code style="background: #101827; color: #2563EB; font-size: 0.8rem; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">{f.get('file', '')}</code>
                        </div>
                        <span style="font-size: 0.75rem; color: #22C55E; font-weight: 700;">{f.get('severity', '')}</span>
                    </div>
                    <div style="font-size: 0.82rem; color: #CBD5E1; margin-top: 4px;">{f.get('finding', '')}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 2px; font-style: italic;">Auditor Context: {f.get('limitation', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
