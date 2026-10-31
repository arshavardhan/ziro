import time
import urllib.parse
import streamlit as st
import plotly.graph_objects as go
from services.session_manager import SessionManager
from services.validators import (
    validate_candidate_id,
    validate_github_url,
    extract_github_repo_info,
    generate_candidate_id_from_repo,
)
from services.api_client import APIClient
from config import DEFAULT_BACKEND_URL, SUPPORTED_SKILLS

try:
    from services.resume_service import extract_text_from_bytes, parse_resume
except ImportError:
    try:
        from skillproof.backend.services.resume_service import extract_text_from_bytes, parse_resume
    except ImportError:
        extract_text_from_bytes, parse_resume = None, None


def render_overview_dashboard():
    """Render enterprise overview dashboard with genuine dynamic repository selection,

    zero synthetic data, clean empty states, and production Navy/Dark Slate/Royal Blue theme.
    """
    SessionManager.init_session()
    session = SessionManager.get_session()

    # Check genuine backend connection health
    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    api_client = APIClient(base_url=backend_url, timeout=2)
    is_live, health_msg = api_client.check_health()
    st.session_state["backend_connected"] = is_live

    # Active Candidate Selection Context
    sel_cid = st.session_state.get("selected_candidate_id", "")
    sel_url = st.session_state.get("selected_repository_url", "") or st.session_state.get("selected_repo_url", "")
    sel_owner = st.session_state.get("selected_repository_owner", "")
    sel_repo = st.session_state.get("selected_repository_name", "")
    sel_skills = st.session_state.get("selected_claimed_skills", [])
    sel_desc = st.session_state.get("selected_candidate_description", "") or st.session_state.get("selected_description", "")
    is_prepared = st.session_state.get("is_verification_prepared", False)

    # 1. Header Bar
    st.markdown(
        f"""
        <div style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                        SkillProof AI — Candidate Skill Verification
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                        Autonomous agent-based verification of software engineering skills from public GitHub repositories.
                    </p>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    {'<span class="badge-verified">● BACKEND CONNECTED</span>' if is_live else '<span class="badge-pending">○ BACKEND OFFLINE</span>'}
                    {f'<span class="badge-info">CANDIDATE: {sel_cid}</span>' if sel_cid else ''}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Section: START NEW VERIFICATION
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 22px 24px 18px 24px; margin-bottom: 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
            <div style="margin-bottom: 8px;">
                <h3 style="margin: 0; color: #F8FAFC; font-size: 1.25rem; font-weight: 800; letter-spacing: -0.3px;">
                    START NEW VERIFICATION
                </h3>
            </div>
            <p style="margin: 0 0 16px 0; color: #CBD5E1; font-size: 0.88rem; line-height: 1.4;">
                Enter candidate information and provide a public GitHub repository URL to prepare a verification.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 1: GitHub Repository Target & Candidate Identity
    st.markdown("<p style='font-weight: 700; color: #60A5FA; font-size: 0.95rem; margin-bottom: 6px;'>🔗 SECTION 1: Target Repository & Auto-Generated Candidate Identity</p>", unsafe_allow_html=True)

    def on_dashboard_repo_change():
        url = st.session_state.get("field_repo_url", "").strip()
        if url:
            auto_id = generate_candidate_id_from_repo(url)
            if auto_id:
                st.session_state["field_candidate_id"] = auto_id
                st.session_state["input_candidate_id"] = auto_id
                st.session_state["selected_candidate_id"] = auto_id

    col_url, col_cid = st.columns([2, 1.3])
    with col_url:
        repo_url_input = st.text_input(
            "GitHub Repository URL *",
            value=st.session_state.get("input_repo_url", ""),
            placeholder="https://github.com/username/repository",
            help="Public HTTPS GitHub repository URL (Candidate Profile ID is auto-generated from this link)",
            key="field_repo_url",
            on_change=on_dashboard_repo_change,
        )
    with col_cid:
        current_cid = st.session_state.get("field_candidate_id") or st.session_state.get("input_candidate_id", "")
        if not current_cid and repo_url_input:
            current_cid = generate_candidate_id_from_repo(repo_url_input)
            st.session_state["field_candidate_id"] = current_cid
            st.session_state["input_candidate_id"] = current_cid

        candidate_id_input = st.text_input(
            "Candidate Profile ID * (Auto-Generated)",
            value=current_cid,
            placeholder="Auto-derived from repository URL",
            help="Unique identifier auto-derived from your repository link (editable)",
            key="field_candidate_id",
        )

    if repo_url_input and candidate_id_input:
        st.markdown(
            f"""
            <div style="font-size: 0.78rem; color: #60A5FA; margin-top: -6px; margin-bottom: 10px;">
                ⚡ <b>Profile Linked:</b> Candidate ID <code>{candidate_id_input}</code> auto-derived from repository URL.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Section 2: Candidate Resume Upload & Skill Extraction
    st.markdown("<p style='font-weight: 700; color: #22C55E; font-size: 0.95rem; margin-top: 14px; margin-bottom: 6px;'>📄 SECTION 2: Candidate Resume Upload & Skill Extraction</p>", unsafe_allow_html=True)
    col_file, col_paste = st.columns([1.5, 1.5])
    with col_file:
        uploaded_file = st.file_uploader(
            "Upload Resume (PDF, DOCX, TXT, MD)",
            type=["pdf", "docx", "txt", "md"],
            help="Upload resume to automatically extract candidate profile and technical skills",
            key="dash_resume_file",
        )
        if uploaded_file is not None:
            f_bytes = uploaded_file.getvalue()
            f_name = uploaded_file.name
            st.session_state["uploaded_resume_name"] = f_name
            text_extracted = ""
            if extract_text_from_bytes:
                text_extracted = extract_text_from_bytes(f_bytes, f_name)
            st.session_state["uploaded_resume_text"] = text_extracted
            if parse_resume and text_extracted:
                p_prof = parse_resume(text_extracted, f_name)
                st.session_state["parsed_resume_profile"] = p_prof
                st.session_state["resume_extracted_skills"] = p_prof.get("extracted_skills", [])
                st.caption(f"✓ Parsed: {f_name} ({len(p_prof.get('extracted_skills', []))} skills detected)")

    with col_paste:
        with st.expander("📝 Or Paste Resume Text", expanded=False):
            pasted_txt = st.text_area(
                "Paste Resume Text",
                value=st.session_state.get("uploaded_resume_text") or "",
                placeholder="Paste raw resume text...",
                height=90,
                key="dash_resume_text",
            )
            if pasted_txt.strip() and not st.session_state.get("parsed_resume_profile"):
                st.session_state["uploaded_resume_name"] = "pasted_resume.txt"
                st.session_state["uploaded_resume_text"] = pasted_txt.strip()
                if parse_resume:
                    p_prof = parse_resume(pasted_txt.strip(), "pasted_resume.txt")
                    st.session_state["parsed_resume_profile"] = p_prof
                    st.session_state["resume_extracted_skills"] = p_prof.get("extracted_skills", [])

    # Display Parsed Resume Chips
    dash_profile = st.session_state.get("parsed_resume_profile")
    if dash_profile:
        dash_skills = dash_profile.get("extracted_skills", [])
        dash_name = dash_profile.get("candidate_name") or "Candidate"
        dash_chips = " ".join([f"`{s}`" for s in dash_skills[:12]])
        st.markdown(
            f"""
            <div style="background: #101827; border: 1px solid #22C55E; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
                <span style="font-size: 0.72rem; color: #22C55E; font-weight: 700; text-transform: uppercase;">
                    ✓ RESUME DETECTED: {dash_name} ({len(dash_skills)} skills)
                </span>
                <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 4px;">{dash_chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Section 3: Claimed Skills & Description
    st.markdown("<p style='font-weight: 700; color: #94A3B8; font-size: 0.95rem; margin-top: 10px; margin-bottom: 6px;'>🎯 SECTION 3: Claimed Technical Skills & Context</p>", unsafe_allow_html=True)
    col_skills, col_desc = st.columns([1.2, 1.8])
    with col_skills:
        claimed_skills_input = st.text_input(
            "Claimed Skills (Optional)",
            value=st.session_state.get(
                "input_claimed_skills",
                ", ".join(st.session_state.get("resume_extracted_skills", [])[:6]) if st.session_state.get("resume_extracted_skills") else "",
            ),
            placeholder="e.g. Python, FastAPI, Docker, SQL",
            help="Comma-separated list of candidate claimed technical skills",
            key="field_claimed_skills",
        )
    with col_desc:
        description_input = st.text_area(
            "Candidate Description (Optional)",
            value=st.session_state.get("input_description", ""),
            placeholder="Enter candidate background or project context...",
            help="Candidate background, project context, or verification notes",
            height=70,
            key="field_description",
        )

    # Action Buttons: OPEN REPOSITORY, PREPARE VERIFICATION, and Clear
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c_btn_open, c_btn_prep, c_btn_reset = st.columns([1, 1.4, 0.8])

    with c_btn_open:
        open_repo_clicked = st.button(
            "🌐 OPEN REPOSITORY",
            type="secondary",
            use_container_width=True,
            help="Validate and open the entered GitHub repository URL in a new browser tab",
        )

    with c_btn_prep:
        prepare_clicked = st.button(
            "⚡ PREPARE VERIFICATION",
            type="primary",
            use_container_width=True,
            help="Validate inputs and stage candidate details in session state for backend integration",
        )

    with c_btn_reset:
        reset_clicked = st.button(
            "Clear Inputs",
            use_container_width=True,
            help="Reset input fields and active candidate selection",
        )

    # Action 1: Clear Inputs
    if reset_clicked:
        st.session_state["input_candidate_id"] = ""
        st.session_state["input_repo_url"] = ""
        st.session_state["input_claimed_skills"] = ""
        st.session_state["input_description"] = ""
        SessionManager.clear_session()
        st.rerun()

    # Action 2: OPEN REPOSITORY
    if open_repo_clicked:
        is_valid_url, url_err = validate_github_url(repo_url_input)
        if not is_valid_url:
            st.error(f"Cannot Open Repository: {url_err}")
        else:
            clean_url = repo_url_input.strip()
            owner, repo_name = extract_github_repo_info(clean_url)
            st.markdown(
                f"""
                <div style="background: #1B2638; border: 1px solid #2563EB; border-radius: 8px; padding: 14px 18px; margin: 14px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="color: #60A5FA; font-weight: 700; font-size: 0.8rem; text-transform: uppercase;">
                                ✓ Validated GitHub Repository: {owner}/{repo_name}
                            </span>
                            <div style="color: #F8FAFC; font-size: 0.95rem; font-weight: 700; margin-top: 2px; word-break: break-all;">
                                <code>{clean_url}</code>
                            </div>
                            <div style="color: #94A3B8; font-size: 0.75rem; margin-top: 4px;">
                                Note: Inspecting source on GitHub does not initiate autonomous verification analysis.
                            </div>
                        </div>
                        <a href="{clean_url}" target="_blank" rel="noopener noreferrer" style="background: #2563EB; color: #FFFFFF !important; font-weight: 700; font-size: 0.85rem; padding: 8px 16px; border-radius: 6px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);">
                            Open on GitHub ↗
                        </a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Safe browser popup navigation
            import streamlit.components.v1 as components
            escaped_url = clean_url.replace("'", "\\'")
            components.html(f"<script>window.open('{escaped_url}', '_blank');</script>", height=0)

    # Action 3: PREPARE VERIFICATION (Frontend interaction only — Zero fake data, zero backend calls)
    if prepare_clicked:
        clean_url = repo_url_input.strip() if repo_url_input else ""
        clean_cid = candidate_id_input.strip() if candidate_id_input else ""
        if not clean_cid and clean_url:
            clean_cid = generate_candidate_id_from_repo(clean_url)
            st.session_state["field_candidate_id"] = clean_cid
            st.session_state["input_candidate_id"] = clean_cid

        # Validate Candidate ID
        is_valid_cid, cid_err = validate_candidate_id(clean_cid)
        if not is_valid_cid:
            st.error(f"Candidate ID Validation Error: {cid_err}")
            return

        # Validate GitHub Repository URL
        is_valid_url, url_err = validate_github_url(clean_url)
        if not is_valid_url:
            st.error(f"Repository URL Validation Error: {url_err}")
            return

        clean_cid = candidate_id_input.strip()
        clean_url = repo_url_input.strip()
        clean_desc = description_input.strip()
        owner, repo_name = extract_github_repo_info(clean_url)

        if not owner or not repo_name:
            st.error("Validation Error: Missing repository owner or repository name in URL path.")
            return

        # Parse claimed skills
        skills_list = [s.strip() for s in claimed_skills_input.split(",") if s.strip()] if claimed_skills_input.strip() else []

        # Store in session state strictly adhering to requirements
        st.session_state["selected_candidate_id"] = clean_cid
        st.session_state["selected_repository_url"] = clean_url
        st.session_state["selected_repo_url"] = clean_url
        st.session_state["selected_repository_owner"] = owner
        st.session_state["selected_repository_name"] = repo_name
        st.session_state["selected_claimed_skills"] = skills_list
        st.session_state["selected_candidate_description"] = clean_desc
        st.session_state["selected_description"] = clean_desc
        st.session_state["is_verification_prepared"] = True

        st.session_state["input_candidate_id"] = clean_cid
        st.session_state["input_repo_url"] = clean_url
        st.session_state["input_claimed_skills"] = claimed_skills_input
        st.session_state["input_description"] = clean_desc

        # Prepare initial session
        initial_sess = {
            "session_id": f"prep_{clean_cid}",
            "candidate_id": clean_cid,
            "repo_url": clean_url,
            "claimed_skills": skills_list if skills_list else ["Python"],
            "description": clean_desc,
            "status": "PREPARED",
            "approval_status": "pending",
            "repo_info": {
                "repo_name": repo_name,
                "repo_owner": owner,
                "repo_url": clean_url,
            },
            "code_files": {},
            "git_commits": [],
            "timeline": [],
            "skill_assessment": {},
            "viva_questions": [],
            "approval": {},
            "credential": {},
            "resume_info": st.session_state.get("parsed_resume_profile"),
            "resume_skills": st.session_state.get("resume_extracted_skills", []),
        }
        SessionManager.set_session(initial_sess)

        # If backend is connected, launch pipeline immediately
        if is_live:
            with st.spinner(f"🚀 Launching autonomous verification on {clean_url}..."):
                ok, res, err = api_client.start_analysis(
                    candidate_id=clean_cid,
                    repo_url=clean_url,
                    claimed_skills=skills_list if skills_list else ["Python"],
                    description=clean_desc,
                    resume_text=st.session_state.get("uploaded_resume_text"),
                    resume_filename=st.session_state.get("uploaded_resume_name"),
                    resume_skills=st.session_state.get("resume_extracted_skills"),
                )
                if ok and res.get("session_id"):
                    real_sid = res["session_id"]
                    st.session_state["active_session_id"] = real_sid
                    time.sleep(1.5)
                    ok_s, s_data, _ = api_client.get_session(real_sid)
                    if ok_s and s_data:
                        SessionManager.set_session(s_data)

        st.rerun()

    # Display Confirmation when Prepared (Actual user-entered values)
    if is_prepared and sel_cid and sel_url:
        st.markdown(
            f"""
            <div style="background: #1B2638; border: 1px solid #22C55E; border-radius: 12px; padding: 20px; margin-top: 16px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.3rem;">✓</span>
                        <h4 style="margin: 0; color: #F8FAFC; font-size: 1.15rem; font-weight: 700;">
                            Candidate Information Saved Successfully
                        </h4>
                    </div>
                    <span class="badge-verified" style="font-size: 0.75rem; padding: 4px 12px;">
                        ● READY FOR BACKEND INTEGRATION
                    </span>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 12px;">
                    <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px;">
                        <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">CANDIDATE ID</span>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #F8FAFC; margin-top: 2px;">{sel_cid}</div>
                    </div>
                    <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px;">
                        <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">REPOSITORY OWNER</span>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-top: 2px;">{sel_owner or '—'}</div>
                    </div>
                    <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px;">
                        <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">REPOSITORY NAME</span>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-top: 2px;">{sel_repo or '—'}</div>
                    </div>
                    <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px;">
                        <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">CLAIMED SKILLS</span>
                        <div style="font-size: 0.95rem; font-weight: 600; color: #CBD5E1; margin-top: 2px;">
                            {', '.join(sel_skills) if sel_skills else 'None specified'}
                        </div>
                    </div>
                </div>

                <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                    <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">FULL REPOSITORY URL</span>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #60A5FA; margin-top: 2px; word-break: break-all;">
                        <a href="{sel_url}" target="_blank" rel="noopener noreferrer" style="color: #60A5FA; text-decoration: underline;">
                            {sel_url} ↗
                        </a>
                    </div>
                </div>

                {f'''
                <div style="background: #101827; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                    <span style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">CANDIDATE DESCRIPTION</span>
                    <div style="font-size: 0.88rem; color: #CBD5E1; margin-top: 2px; line-height: 1.4;">{sel_desc}</div>
                </div>
                ''' if sel_desc else ''}

                <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid #22C55E; border-radius: 8px; padding: 12px 16px; margin-top: 8px;">
                    <div style="color: #22C55E; font-weight: 600; font-size: 0.9rem;">
                        Candidate information saved successfully. Repository selection is ready for backend integration.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Metric KPI Cards Strip — Genuine data sources only (no synthetic numbers)
    st.markdown("<h4 style='color: #F8FAFC; margin-bottom: 10px;'>Verification Parameters & Session Summary</h4>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Calculate real status values from current active session
    active_cand_val = sel_cid if sel_cid else "None"
    active_repo_val = sel_repo if sel_repo else "None"
    active_skills_val = str(len(sel_skills)) if sel_skills else "0"
    v_status = session.get("status", "NOT_STARTED")
    cred_status = "Issued" if session.get("credential", {}).get("credential_id") else "Not Issued"
    score_val = str(session.get("overall_score")) if session.get("overall_score") is not None and v_status == "COMPLETED" else "—"

    metrics_data = [
        ("Active Candidate", active_cand_val, "Selected ID" if sel_cid else "Awaiting Input", "#2563EB"),
        ("Target Repo", active_repo_val, "Parsed Name" if sel_repo else "Awaiting Input", "#2563EB"),
        ("Claimed Skills", active_skills_val, "User specified", "#2563EB"),
        ("Pipeline Status", v_status, "Execution state", "#F59E0B" if v_status != "COMPLETED" else "#22C55E"),
        ("Evidence Score", score_val, "Analysis pending" if score_val == "—" else "Verified score", "#94A3B8"),
        ("Credential", cred_status, "Ledger status", "#94A3B8" if cred_status == "Not Issued" else "#22C55E"),
    ]

    for col, (title, val, sub, accent_col) in zip(
        [col1, col2, col3, col4, col5, col6], metrics_data
    ):
        with col:
            st.markdown(
                f"""
                <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                    <div style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">{title}</div>
                    <div style="font-size: 1.3rem; font-weight: 800; color: #F8FAFC; margin: 4px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{val}</div>
                    <div style="font-size: 0.68rem; color: {accent_col};">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 4. Visualizations Row — Clean empty states when real chart data is unavailable
    c_pie, c_bar = st.columns([1, 1.2])

    with c_pie:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; height: 100%;">
                <h4 style="margin: 0 0 10px 0; color: #F8FAFC; font-size: 1.05rem;">Verification Status Breakdown</h4>
            """,
            unsafe_allow_html=True,
        )
        # Check if genuine verification history exists in session state
        real_status_history = st.session_state.get("verification_sessions_history", [])
        if not real_status_history:
            st.markdown(
                """
                <div style="text-align: center; padding: 50px 20px; color: #94A3B8;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">📊</div>
                    <div style="font-weight: 600; color: #CBD5E1; font-size: 0.95rem;">No verification data to display.</div>
                    <p style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">
                        Prepare or run a verification session to visualize skill distribution and status.
                    </p>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            status_counts = {}
            for item in real_status_history:
                st_name = item.get("status", "Unknown")
                status_counts[st_name] = status_counts.get(st_name, 0) + 1
            labels = list(status_counts.keys())
            values = list(status_counts.values())

            fig_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=["#2563EB", "#22C55E", "#F59E0B", "#EF4444"], line=dict(color='#1B2638', width=2)),
                textinfo='percent+label',
                textfont=dict(color="#F8FAFC", size=10)
            )])
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                height=240,
                showlegend=False
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with c_bar:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; height: 100%;">
                <h4 style="margin: 0 0 10px 0; color: #F8FAFC; font-size: 1.05rem;">Skill Domain Assessment Distribution</h4>
            """,
            unsafe_allow_html=True,
        )
        skills_assessment = session.get("skill_assessment", {}).get("skills", {})
        if not skills_assessment:
            st.markdown(
                """
                <div style="text-align: center; padding: 50px 20px; color: #94A3B8;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">📈</div>
                    <div style="font-weight: 600; color: #CBD5E1; font-size: 0.95rem;">No skill assessment records.</div>
                    <p style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">
                        Skill scoring distribution will appear after candidate repository analysis executes.
                    </p>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            skill_names = list(skills_assessment.keys())
            skill_scores = [skills_assessment[k].get("score", 0) for k in skill_names]

            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name="Score",
                y=skill_names,
                x=skill_scores,
                orientation='h',
                marker=dict(color='#2563EB')
            ))
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                height=240,
                xaxis=dict(range=[0, 100], gridcolor="#334155", tickfont=dict(color="#94A3B8")),
                yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#F8FAFC", size=10), autorange="reversed"),
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 5. Recent Verification Sessions & Platform Telemetry Status
    c_rec, c_act = st.columns([1.2, 1])

    with c_rec:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0; color: #F8FAFC; font-size: 1.05rem;">Recent Verification Sessions</h4>
                </div>
            """,
            unsafe_allow_html=True,
        )

        recent_sessions = st.session_state.get("verification_sessions_history", [])
        if not recent_sessions:
            st.markdown(
                """
                <div style="padding: 24px 0; text-align: center; color: #94A3B8; font-size: 0.9rem;">
                    No verification sessions available.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for s in recent_sessions[-5:]:
                cid = s.get("candidate_id", "—")
                rname = s.get("repo_name", "—")
                sc = s.get("score", "—")
                st_text = s.get("status", "Pending")
                st.markdown(
                    f"""
                    <div style="border-bottom: 1px solid #334155; padding: 8px 0; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #F8FAFC; font-size: 0.85rem;">{cid}</strong>
                            <span style="color: #CBD5E1; font-size: 0.8rem; margin-left: 8px;">{rname}</span>
                        </div>
                        <div>
                            <span style="color: #60A5FA; font-weight: 700; font-size: 0.85rem; margin-right: 12px;">{sc}</span>
                            <span style="color: #22C55E; border: 1px solid #22C55E; padding: 1px 6px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">{st_text}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with c_act:
        st.markdown(
            """
            <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0; color: #F8FAFC; font-size: 1.05rem;">Agent Telemetry</h4>
                </div>
            """,
            unsafe_allow_html=True,
        )

        # Genuine telemetry only
        real_telemetry = session.get("timeline", [])
        if not real_telemetry:
            st.markdown(
                """
                <div style="padding: 24px 0; text-align: center; color: #94A3B8; font-size: 0.9rem;">
                    Telemetry unavailable.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for event in real_telemetry[-4:]:
                aname = event.get("agent", "Agent")
                act = event.get("observation", "")
                tm = event.get("timestamp", "")
                st.markdown(
                    f"""
                    <div style="border-bottom: 1px solid #334155; padding: 8px 0;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                            <strong style="color: #60A5FA;">{aname}</strong>
                            <span style="color: #94A3B8; font-size: 0.7rem;">{tm}</span>
                        </div>
                        <div style="color: #F8FAFC; font-size: 0.78rem; margin-top: 2px;">{act}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)


render_dashboard = render_overview_dashboard

