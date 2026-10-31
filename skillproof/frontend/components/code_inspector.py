import streamlit as st
from services.session_manager import SessionManager


def render_code_inspector():
    """Render interactive code inspection with AST metrics, complexity, and linked tests."""
    session = SessionManager.get_session()
    code_files = session.get("code_files", {})
    cand_id = session.get("candidate_id") or st.session_state.get("selected_candidate_id", "")

    st.markdown(
        f"""
        <div style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                        AST Code & Architectural Inspector
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                        Static AST decomposition: class hierarchies, cyclomatic complexity, method signatures, and linked verification tests.
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

    if not code_files:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 40px 20px; text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 10px;">🔍</div>
                <h3 style="color: #F8FAFC; margin-bottom: 6px;">No Source Code Files Available</h3>
                <p style="color: #94A3B8; font-size: 0.9rem; max-width: 500px; margin: 0 auto;">
                    Source code files and abstract syntax tree (AST) metrics will be populated once the candidate verification pipeline runs on the backend.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    col_select, _ = st.columns([1.5, 1])
    with col_select:
        selected_file = st.selectbox(
            "Select Source File to Inspect",
            options=list(code_files.keys()),
            index=0,
        )

    ast_info = session.get("ast_metrics", {}).get(
        selected_file,
        {
            "classes": ["ModuleClass"],
            "functions": ["execute"],
            "signatures": ["execute(*args, **kwargs)"],
            "imports": ["typing"],
            "cyclomatic_complexity": 1.0,
            "linked_skills": ["Python"],
            "linked_tests": [],
            "method": "AST Node Visitor",
        },
    )

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 14px 0; color: #F8FAFC; font-size: 1.1rem;">Structural AST Signatures</h4>
                
                <div style="margin-bottom: 12px;">
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Extracted Classes</span>
                    <div style="margin-top: 4px;">
                        {' '.join([f'<code style="background: #0B1220; color: #60A5FA; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; border: 1px solid #334155;">{c}</code>' for c in ast_info['classes']])}
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Key Method Signatures</span>
                    <div style="margin-top: 4px; font-family: monospace; font-size: 0.82rem; color: #CBD5E1; line-height: 1.6;">
                        {'<br>'.join([f'• {s}' for s in ast_info['signatures']])}
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Top-Level Imports</span>
                    <div style="margin-top: 4px;">
                        {' '.join([f'<code style="background: #0B1220; color: #22C55E; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #334155;">{imp}</code>' for imp in ast_info['imports']])}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 14px 0; color: #F8FAFC; font-size: 1.1rem;">Complexity & Verification Evidence</h4>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
                    <div style="background: #0B1220; border: 1px solid #334155; border-radius: 8px; padding: 12px;">
                        <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Cyclomatic Complexity</span>
                        <div style="font-size: 1.4rem; font-weight: 800; color: #22C55E; margin-top: 2px;">{ast_info['cyclomatic_complexity']}</div>
                    </div>
                    <div style="background: #0B1220; border: 1px solid #334155; border-radius: 8px; padding: 12px;">
                        <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Extraction Method</span>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #CBD5E1; margin-top: 4px;">{ast_info.get('method', 'AST Parser')}</div>
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Linked Verified Skills</span>
                    <div style="margin-top: 4px;">
                        {' '.join([f'<span style="background: rgba(37, 99, 235, 0.15); color: #60A5FA; border: 1px solid #2563EB; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">{sk}</span>' for sk in ast_info['linked_skills']])}
                    </div>
                </div>

                <div>
                    <span style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Linked Pytest References</span>
                    <div style="margin-top: 4px;">
                        {' '.join([f'<code style="background: #0B1220; color: #F59E0B; padding: 2px 6px; border-radius: 4px; font-size: 0.78rem; border: 1px solid #334155;">{t}</code>' for t in ast_info.get('linked_tests', [])]) or '<span style="color: #94A3B8; font-size: 0.8rem;">None linked</span>'}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Source Viewer
    st.markdown(
        f"""
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h4 style="margin: 0; color: #F8FAFC; font-size: 1rem;">File Content: <code>{selected_file}</code></h4>
            </div>
        """,
        unsafe_allow_html=True,
    )
    st.code(code_files.get(selected_file, "# No content available"), language="python", line_numbers=True)
    st.markdown("</div>", unsafe_allow_html=True)
