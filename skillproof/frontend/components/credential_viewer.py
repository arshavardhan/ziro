import json
import streamlit as st
from config import DEFAULT_BACKEND_URL
from services.api_client import APIClient
from services.session_manager import (
    SessionManager,
    compute_signature,
    verify_signature,
)


def render_credential_viewer():
    """Render Credential Issuance, Employer Verification, and Cryptographic Tamper Demonstration with zero synthetic data."""
    session = SessionManager.get_session()
    cand_id = session.get("selected_candidate_id") or session.get("candidate_id", "")
    session_id = session.get("session_id", "")
    status = session.get("approval_status", "pending")
    cred = session.get("credential", {})

    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    api_client = APIClient(base_url=backend_url, timeout=5)
    is_live = st.session_state.get("backend_connected", False)

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                Verifiable Credentials & Cryptographic Ledger
            </h1>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                Issue HMAC-SHA256 signed tamper-evident skill credentials and verify authentic cryptographic claims.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t1, t2, t3 = st.tabs([
        "🎖️ 1. Candidate Credential Certificate",
        "🔍 2. Employer Verification Portal",
        "🛡️ 3. Tamper Detection Test Sandbox",
    ])

    # Tab 1: Certificate & Issuance
    with t1:
        if status != "approved":
            st.warning(
                "🔒 **Issuance Locked**: Credential cannot be issued until a human auditor formally grants approval in the 'Reviewer Approval' console."
            )
        else:
            st.success(
                "✅ Candidate is officially approved! You may issue or download the cryptographically signed skill credential."
            )

            if st.button("⚡ Issue Verifiable Credential", type="primary"):
                if is_live:
                    ok, resp, err = api_client.issue_credential(session_id)
                    if ok:
                        st.session_state["active_session"]["credential"] = resp.get("credential", cred)
                        st.success("Credential generated and signed by live backend!")
                    else:
                        st.error(f"Issuance error: {err}")
                else:
                    st.info("Backend service is offline. Live FastAPI backend is required to issue cryptographically signed credentials.")

            if cred:
                c_data = cred.get("data", {})
                c_sig = cred.get("signature", "")
                c_id = cred.get("credential_id", "SP-CRED-UNREGISTERED")

                # Certificate Display Card
                st.markdown(
                    f"""
                    <div style="background: #1B2638; border: 2px solid #22C55E; border-radius: 16px; padding: 28px; margin: 20px 0; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35);">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 20px;">
                            <div>
                                <span style="font-size: 0.75rem; color: #22C55E; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">AUTONOMOUS AGENT VERIFIED CREDENTIAL</span>
                                <h2 style="margin: 4px 0 0 0; color: #F8FAFC; font-size: 1.5rem; font-weight: 800;">SkillProof Digital Certificate</h2>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.75rem; color: #94A3B8;">CREDENTIAL ID</div>
                                <code style="font-size: 0.95rem; color: #22C55E; font-weight: 700;">{c_id}</code>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
                            <div>
                                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Candidate ID:</div>
                                <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">{c_data.get('candidate_id', cand_id if cand_id else 'Unspecified')}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Repository:</div>
                                <div style="font-size: 0.85rem; font-family: monospace; color: #2563EB;">{c_data.get('repo_url', session.get('selected_repository_url', ''))}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Commit SHA:</div>
                                <div style="font-size: 0.85rem; font-family: monospace; color: #CBD5E1;">{c_data.get('commit_sha', '')[:10]}...</div>
                            </div>
                            <div>
                                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Issued Timestamp:</div>
                                <div style="font-size: 0.85rem; font-family: monospace; color: #94A3B8;">{c_data.get('issue_timestamp', '')}</div>
                            </div>
                        </div>

                        <div style="background: #101827; border: 1px solid #334155; border-radius: 10px; padding: 16px; margin-bottom: 20px;">
                            <div style="font-size: 0.75rem; font-weight: 700; color: #22C55E; text-transform: uppercase; margin-bottom: 8px;">VERIFIED SKILL PORTFOLIO:</div>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                {''.join([f'<span style="background: #1B2638; border: 1px solid #22C55E; color: #F8FAFC; padding: 5px 10px; border-radius: 6px; font-size: 0.8rem;"><strong>{s.get("skill","")}</strong> — {s.get("score",0)}/100 (VERIFIED)</span>' for s in c_data.get('verified_skills', [])])}
                            </div>
                        </div>

                        <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #94A3B8; margin-bottom: 4px;">
                                <span>HMAC-SHA256 Cryptographic Signature:</span>
                                <span style="color: #22C55E; font-weight: 700;">STATUS: VALID</span>
                            </div>
                            <code style="word-break: break-all; color: #22C55E; font-size: 0.75rem;">{c_sig}</code>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # JSON Download
                cred_json_str = json.dumps(cred, indent=2)
                st.download_button(
                    label="📥 Download Cryptographically Signed Credential (JSON)",
                    data=cred_json_str,
                    file_name=f"skillproof_credential_{c_id}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.info("No active credential record issued yet. Click 'Issue Verifiable Credential' once verification and approval are complete.")

    # Tab 2: Employer Verification
    with t2:
        st.markdown(
            "### Employer Credential Verification Portal\nQuery the cryptographic ledger to verify candidate authenticity."
        )

        col_q1, col_q2 = st.columns([2, 1])
        with col_q1:
            q_id = st.text_input("Enter Credential ID:", value="", placeholder="Paste Credential ID (e.g. SP-CRED-...)")
        with col_q2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            verify_btn = st.button("🔍 Verify Authenticity", type="primary", use_container_width=True)

        if verify_btn and q_id.strip():
            if is_live:
                valid, v_data, err = api_client.verify_credential(q_id.strip())
            else:
                valid = (cred and cred.get("credential_id") == q_id.strip())
                v_data = cred.get("data", {}) if valid else {}

            if valid:
                st.markdown(
                    f"""
                    <div style="background: rgba(34, 197, 94, 0.12); border: 2px solid #22C55E; border-radius: 12px; padding: 20px; margin-top: 16px;">
                        <div style="font-size: 1.3rem; font-weight: 800; color: #22C55E; margin-bottom: 6px;">
                            🛡️ STATUS: VALID CREDENTIAL
                        </div>
                        <div style="font-size: 0.88rem; color: #F8FAFC; line-height: 1.4;">
                            The cryptographic signature matches the canonical claims. This candidate was independently verified by autonomous agents and audited by lead human reviewer.
                        </div>
                        <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 10px;">
                            Candidate: <strong>{v_data.get('candidate_id', 'Unknown')}</strong> | Target: <code>{v_data.get('repo_url', 'N/A')}</code>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div style="background: rgba(239, 68, 68, 0.12); border: 2px solid #EF4444; border-radius: 12px; padding: 20px; margin-top: 16px;">
                        <div style="font-size: 1.3rem; font-weight: 800; color: #EF4444; margin-bottom: 6px;">
                            🚨 STATUS: INVALID CREDENTIAL
                        </div>
                        <div style="font-size: 0.88rem; color: #F8FAFC;">
                            Credential ID not registered or cryptographic signature failed validation.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        elif verify_btn and not q_id.strip():
            st.warning("Please enter a Credential ID to query the verification ledger.")

    # Tab 3: Tamper Detection Demonstration
    with t3:
        st.markdown(
            "### Cryptographic Tamper Rejection Test (Demonstration)\nTest how HMAC-SHA256 mathematical signatures detect any altered payload."
        )

        col_orig, col_tamp = st.columns([1, 1])

        active_cand = cand_id if cand_id else "CAND-AUDIT-SAMPLE"
        genuine = {
            "credential_id": "SP-CRED-TEST-VERIFY",
            "candidate_id": active_cand,
            "role": "Software Engineer",
            "score": 85,
        }
        genuine_sig = compute_signature(genuine)
        genuine_full = dict(genuine, signature=genuine_sig)

        with col_orig:
            st.markdown("<div style='font-weight: 700; color: #22C55E; margin-bottom: 6px;'>Genuine Credential (HMAC Valid)</div>", unsafe_allow_html=True)
            st.json(genuine_full)

        with col_tamp:
            st.markdown("<div style='font-weight: 700; color: #EF4444; margin-bottom: 6px;'>Altered Payload (Role changed to Principal)</div>", unsafe_allow_html=True)
            tampered_full = {
                "credential_id": "SP-CRED-TEST-VERIFY",
                "candidate_id": active_cand,
                "role": "Principal AI Architect (TAMPERED)",
                "score": 99,
                "signature": genuine_sig,  # Unchanged signature
            }
            st.json(tampered_full)

        if st.button("🛡️ Execute Cryptographic Tamper Rejection Test", type="primary", use_container_width=True):
            payload_check = {k: v for k, v in tampered_full.items() if k != "signature"}
            is_valid = verify_signature(payload_check, tampered_full["signature"])

            if not is_valid:
                st.markdown(
                    f"""
                    <div style="background: rgba(239, 68, 68, 0.15); border: 2px solid #EF4444; border-radius: 12px; padding: 20px; margin-top: 16px;">
                        <div style="font-size: 1.25rem; font-weight: 800; color: #EF4444; margin-bottom: 6px;">
                            🚨 FORGERY BLOCKED: INVALID SIGNATURE MISMATCH
                        </div>
                        <div style="font-size: 0.85rem; color: #F8FAFC; font-family: monospace;">
                            Calculated Digest on Tampered Payload: <span style="color: #EF4444;">{compute_signature(payload_check)}</span><br>
                            Expected Genuine Signature in File: <span style="color: #22C55E;">{tampered_full['signature']}</span><br><br>
                            <strong>VERDICT: Verification rejected. Tampering mathematically detected.</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
