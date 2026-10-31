import streamlit as st
from services.session_manager import SessionManager


def render_test_results():
    """Render automated test harness execution report with zero synthetic data."""
    session = SessionManager.get_session()
    test_data = session.get("test_results", {})
    cases = test_data.get("cases", [])

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                Automated Test Verification
            </h1>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                Sandboxed pytest suite execution verifying mathematical bounds, detector polymorphism, and numerical stability.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not cases:
        st.info("No test execution results available. Sandboxed test suite will execute during backend verification.")
        return

    total = test_data.get("total", len(cases))
    passed = test_data.get("passed", sum(1 for c in cases if c.get("status") == "PASSED"))
    cov = test_data.get("coverage", "N/A")
    duration = test_data.get("duration", "N/A")
    runner = test_data.get("runner", "Pytest")

    # Test Metric Summary
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Test Suite Status</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #22C55E; margin: 4px 0;">{passed} / {total} Passed</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">Pass Rate: {(passed / total * 100) if total else 0:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Code Coverage</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #2563EB; margin: 4px 0;">{cov}</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">Harness branch coverage</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Execution Time</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; margin: 4px 0;">{duration}</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">Execution duration</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Test Runner</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; margin: 4px 0;">{runner}</div>
                <div style="font-size: 0.7rem; color: #CBD5E1;">Execution engine</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Test cases table
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px;">
            <h4 style="margin: 0 0 16px 0; color: #F8FAFC; font-size: 1.05rem;">Executed Test Cases & Assertions</h4>
        """,
        unsafe_allow_html=True,
    )

    for tc in cases:
        status = tc.get("status", "PASSED")
        s_color = "#22C55E" if status == "PASSED" else "#EF4444"
        badge_cls = "badge-verified" if status == "PASSED" else "badge-rejected"

        st.markdown(
            f"""
            <div style="border-bottom: 1px solid #334155; padding: 10px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="color: {s_color}; font-weight: 800; font-size: 0.85rem;">✓ {tc.get('name', 'Test')}</span>
                    <span style="color: #94A3B8; font-size: 0.75rem; margin-left: 8px;">({tc.get('file', '')})</span>
                    <div style="font-family: monospace; font-size: 0.75rem; color: #CBD5E1; margin-top: 2px;">{tc.get('assertion', '')}</div>
                </div>
                <div style="text-align: right;">
                    <span class="{badge_cls}">{status}</span>
                    <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 2px;">{tc.get('duration', '')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
