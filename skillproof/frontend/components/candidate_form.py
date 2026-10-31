import time
import uuid
import streamlit as st
from config import DEFAULT_BACKEND_URL, SUPPORTED_SKILLS
from services.api_client import APIClient
from services.session_manager import SessionManager
from services.validators import (
    validate_candidate_id,
    validate_github_url,
    extract_github_repo_info,
    generate_candidate_id_from_repo,
)

# Local fallback parser for zero-latency client-side resume extraction
try:
    from services.resume_service import extract_text_from_bytes, parse_resume
except ImportError:
    try:
        from skillproof.backend.services.resume_service import extract_text_from_bytes, parse_resume
    except ImportError:
        extract_text_from_bytes, parse_resume = None, None


def render_candidate_submission_form():
    """Render the Candidate Verification input form with 2 distinct sections:

    1. Paste GitHub Repository Link & Candidate Identity
    2. Upload Candidate Resume (PDF, DOCX, TXT) with automatic skill extraction
    Followed by Claimed Skills selection and Pipeline Dispatch.
    """
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
                Candidate Submission & Verification Dispatch
            </h1>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.95rem;">
                Cross-verify candidate resume claims against real GitHub code evidence, AST syntax findings, RAG retrieval, and git forensics.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    backend_url = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    api_client = APIClient(base_url=backend_url, timeout=5)
    is_live = st.session_state.get("backend_connected", False)

    if not is_live:
        st.info(
            f"⚡ **Backend Notice**: The verification backend at `{backend_url}` is currently offline. "
            "You can prepare parameters and upload a resume. Full verification executes when backend is active.",
            icon="ℹ️",
        )

    # =========================================================================
    # SECTION 1: PASTE GITHUB REPOSITORY LINK & CANDIDATE IDENTITY
    # =========================================================================
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span style="font-size: 1.25rem;">🔗</span>
                <h3 style="margin: 0; color: #F8FAFC; font-size: 1.15rem; font-weight: 700;">
                    SECTION 1: GitHub Repository Target & Candidate Identity
                </h3>
            </div>
            <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 0; margin-bottom: 16px;">
                Provide the public GitHub repository URL containing the candidate's actual source code.
            </p>
        """,
        unsafe_allow_html=True,
    )

    def on_cf_repo_url_change():
        url = st.session_state.get("cf_repo_url", "").strip()
        if url:
            auto_id = generate_candidate_id_from_repo(url)
            if auto_id:
                st.session_state["cf_candidate_id"] = auto_id
                st.session_state["input_candidate_id"] = auto_id
                st.session_state["selected_candidate_id"] = auto_id

    col_url, col_cid = st.columns([2, 1.3])
    with col_url:
        repo_url = st.text_input(
            "GitHub Repository URL *",
            value=st.session_state.get(
                "selected_repository_url", st.session_state.get("input_repo_url", "")
            ),
            placeholder="https://github.com/username/repository",
            help="Public HTTPS GitHub repository URL (Candidate Profile ID auto-generates from this link)",
            key="cf_repo_url",
            on_change=on_cf_repo_url_change,
        )
    with col_cid:
        current_cid = st.session_state.get("cf_candidate_id") or st.session_state.get("selected_candidate_id") or st.session_state.get("input_candidate_id", "")
        if not current_cid and repo_url:
            current_cid = generate_candidate_id_from_repo(repo_url)
            st.session_state["cf_candidate_id"] = current_cid
            st.session_state["input_candidate_id"] = current_cid

        cand_id = st.text_input(
            "Candidate Profile ID * (Auto-Generated)",
            value=current_cid,
            placeholder="Auto-derived from repository URL",
            help="Unique identifier auto-derived from your repository link (editable)",
            key="cf_candidate_id",
        )

    if repo_url and cand_id:
        st.markdown(
            f"""
            <div style="font-size: 0.78rem; color: #60A5FA; margin-top: -6px; margin-bottom: 8px;">
                ⚡ <b>Profile Linked:</b> Candidate ID <code>{cand_id}</code> auto-derived from repository URL.
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_sha, col_preview = st.columns([1.5, 1.5])
    with col_sha:
        commit_sha = st.text_input(
            "Pinned Commit SHA (Optional)",
            value=st.session_state.get("selected_commit_sha", ""),
            placeholder="Optional 40-char commit SHA (HEAD pinned if omitted)",
            help="Full 40-character hexadecimal git commit SHA to ensure immutable reproducible assessment",
            key="cf_commit_sha",
        )
    with col_preview:
        if repo_url and repo_url.startswith("https://github.com/"):
            clean_url = repo_url.strip()
            owner, name = extract_github_repo_info(clean_url)
            st.markdown(
                f"""
                <div style="margin-top: 26px;">
                    <a href="{clean_url}" target="_blank" rel="noopener noreferrer" style="background: #2563EB; color: #FFFFFF !important; font-size: 0.85rem; font-weight: 700; padding: 8px 14px; border-radius: 6px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
                        Open Repository on GitHub ↗ ({owner}/{name})
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # SECTION 2: RESUME UPLOAD & SKILL EXTRACTION
    # =========================================================================
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span style="font-size: 1.25rem;">📄</span>
                <h3 style="margin: 0; color: #F8FAFC; font-size: 1.15rem; font-weight: 700;">
                    SECTION 2: Candidate Resume Upload & Skill Extraction
                </h3>
            </div>
            <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 0; margin-bottom: 16px;">
                Upload candidate resume (PDF, DOCX, TXT, MD) to extract candidate profile and claimed technical skills.
            </p>
        """,
        unsafe_allow_html=True,
    )

    resume_file = st.file_uploader(
        "Upload Resume Document (PDF, DOCX, TXT, MD)",
        type=["pdf", "docx", "txt", "md"],
        help="Upload candidate resume file to automatically parse skills and experience",
        key="cf_resume_file",
    )

    with st.expander("📝 Or Paste Resume Text Directly", expanded=False):
        resume_text_pasted = st.text_area(
            "Paste Raw Resume Text",
            value=st.session_state.get("uploaded_resume_text") or "",
            placeholder="Paste raw resume text here...",
            height=120,
            key="cf_resume_text_area",
        )

    # Process uploaded or pasted resume
    if resume_file is not None:
        file_bytes = resume_file.getvalue()
        filename = resume_file.name
        st.session_state["uploaded_resume_name"] = filename

        # Extract text
        extracted_text = ""
        if extract_text_from_bytes:
            extracted_text = extract_text_from_bytes(file_bytes, filename)
        st.session_state["uploaded_resume_text"] = extracted_text

        # Parse profile via backend API or local parser
        parsed = None
        if is_live:
            ok, resp, err = api_client.parse_resume(file_bytes=file_bytes, filename=filename)
            if ok and "profile" in resp:
                parsed = resp["profile"]
        if not parsed and parse_resume and extracted_text:
            parsed = parse_resume(extracted_text, filename)

        if parsed:
            st.session_state["parsed_resume_profile"] = parsed
            st.session_state["resume_extracted_skills"] = parsed.get("extracted_skills", [])
            st.success(f"✓ Resume successfully parsed: `{filename}` ({len(parsed.get('extracted_skills', []))} skills detected)")

    elif resume_text_pasted.strip() and not st.session_state.get("parsed_resume_profile"):
        extracted_text = resume_text_pasted.strip()
        st.session_state["uploaded_resume_name"] = "pasted_resume.txt"
        st.session_state["uploaded_resume_text"] = extracted_text

        parsed = None
        if is_live:
            ok, resp, err = api_client.parse_resume(resume_text=extracted_text, filename="pasted_resume.txt")
            if ok and "profile" in resp:
                parsed = resp["profile"]
        if not parsed and parse_resume:
            parsed = parse_resume(extracted_text, "pasted_resume.txt")

        if parsed:
            st.session_state["parsed_resume_profile"] = parsed
            st.session_state["resume_extracted_skills"] = parsed.get("extracted_skills", [])
            st.success(f"✓ Resume text parsed ({len(parsed.get('extracted_skills', []))} skills detected)")

    # Display Parsed Resume Card if Available
    parsed_profile = st.session_state.get("parsed_resume_profile")
    if parsed_profile:
        cand_name = parsed_profile.get("candidate_name") or "Unknown"
        cand_email = parsed_profile.get("email") or "Not found"
        cand_phone = parsed_profile.get("phone") or "Not found"
        extracted_skills = parsed_profile.get("extracted_skills", [])

        st.markdown(
            f"""
            <div style="background: #101827; border: 1px solid #22C55E; border-radius: 8px; padding: 14px 18px; margin: 12px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <span style="font-size: 0.7rem; color: #22C55E; font-weight: 700; text-transform: uppercase;">
                            ✓ PARSED RESUME PROFILE
                        </span>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #F8FAFC; margin-top: 2px;">
                            {cand_name}
                        </div>
                        <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 2px;">
                            📧 {cand_email} | 📞 {cand_phone}
                        </div>
                    </div>
                    <span class="badge-verified" style="font-size: 0.75rem; padding: 4px 10px;">
                        {len(extracted_skills)} SKILLS DETECTED
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show detected skills as interactive pill tags
        if extracted_skills:
            st.markdown("<p style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; margin-bottom: 6px;'>DETECTED SKILLS IN RESUME:</p>", unsafe_allow_html=True)
            tags_html = "".join([
                f'<span style="background: #1E293B; border: 1px solid #3B82F6; color: #93C5FD; padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; display: inline-block; margin: 3px;">{s}</span>'
                for s in extracted_skills
            ])
            st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)

            if st.button("⚡ Apply Resume Skills to Claimed Skills", key="btn_apply_resume_skills"):
                st.session_state["selected_claimed_skills"] = extracted_skills
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # SECTION 3: CLAIMED SKILLS & LAUNCH PIPELINE
    # =========================================================================
    st.markdown(
        """
        <div style="background: #1B2638; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span style="font-size: 1.25rem;">🎯</span>
                <h3 style="margin: 0; color: #F8FAFC; font-size: 1.15rem; font-weight: 700;">
                    SECTION 3: Claimed Skills to Verify & Pipeline Launch
                </h3>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Merge supported skills with any extra skills discovered on resume
    all_skill_options = sorted(list(set(SUPPORTED_SKILLS + st.session_state.get("resume_extracted_skills", []))))

    default_skills = st.session_state.get(
        "selected_claimed_skills",
        st.session_state.get("resume_extracted_skills", [])[:5] if st.session_state.get("resume_extracted_skills") else ["Python", "Software Architecture"],
    )

    claimed_skills = st.multiselect(
        "Claimed Skills to Cross-Verify Against Repository Code",
        options=all_skill_options,
        default=[s for s in default_skills if s in all_skill_options],
        help="Select skills to verify using AST code analysis, RAG retrieval, and technical viva",
        key="cf_claimed_skills",
    )

    description = st.text_area(
        "Candidate Notes / Project Context (Optional)",
        value=st.session_state.get(
            "selected_candidate_description", st.session_state.get("input_description", "")
        ),
        height=70,
        placeholder="Enter relevant project context or verification focus areas...",
        key="cf_desc",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Launch Action Button
    launch_clicked = st.button(
        "🚀 Launch Autonomous Verification Pipeline (POST /api/analyze)",
        type="primary",
        use_container_width=True,
    )

    if launch_clicked:
        clean_url = repo_url.strip() if repo_url else ""
        clean_cid = cand_id.strip() if cand_id else ""
        if not clean_cid and clean_url:
            clean_cid = generate_candidate_id_from_repo(clean_url)
            st.session_state["cf_candidate_id"] = clean_cid
            st.session_state["input_candidate_id"] = clean_cid

        is_valid_cid, cid_err = validate_candidate_id(clean_cid)
        if not is_valid_cid:
            st.error(f"Candidate ID Validation Error: {cid_err}")
            return

        is_valid_url, url_err = validate_github_url(clean_url)
        if not is_valid_url:
            st.error(f"Repository URL Validation Error: {url_err}")
            return

        clean_cid = cand_id.strip()
        clean_url = repo_url.strip()
        clean_sha = commit_sha.strip() if commit_sha.strip() else None
        clean_desc = description.strip()
        owner, repo_name = extract_github_repo_info(clean_url)

        # Update session state
        st.session_state["selected_candidate_id"] = clean_cid
        st.session_state["selected_repository_url"] = clean_url
        st.session_state["selected_repo_url"] = clean_url
        st.session_state["selected_commit_sha"] = clean_sha
        st.session_state["selected_repository_owner"] = owner
        st.session_state["selected_repository_name"] = repo_name
        st.session_state["selected_claimed_skills"] = claimed_skills
        st.session_state["selected_candidate_description"] = clean_desc
        st.session_state["is_verification_prepared"] = True

        progress_box = st.container()
        with progress_box:
            st.markdown(
                """
                <div style="background: #1B2638; border: 1px solid #2563EB; border-radius: 12px; padding: 20px; margin-top: 16px;">
                    <div style="font-weight: 700; color: #60A5FA; font-size: 1.1rem; margin-bottom: 6px;">
                        🤖 Multi-Agent Pipeline Dispatch
                    </div>
                """,
                unsafe_allow_html=True,
            )
            p_bar = st.progress(0)
            status_text = st.empty()

            resume_text = st.session_state.get("uploaded_resume_text")
            resume_filename = st.session_state.get("uploaded_resume_name")
            resume_skills = st.session_state.get("resume_extracted_skills", [])

            if is_live:
                status_text.text("Calling POST /api/analyze on backend...")
                p_bar.progress(25)
                ok, resp, err = api_client.start_analysis(
                    candidate_id=clean_cid,
                    repo_url=clean_url,
                    claimed_skills=claimed_skills,
                    description=clean_desc,
                    resume_text=resume_text,
                    resume_filename=resume_filename,
                    resume_skills=resume_skills,
                    commit_sha=clean_sha,
                )
                if not ok:
                    st.error(f"Analysis trigger failed: {err}")
                    return

                session_id = resp.get("session_id", f"sess_{clean_cid}")
                st.session_state["current_session_id"] = session_id
                st.success(f"Session established: `{session_id}`. Polling backend for agent execution...")

                for i in range(10):
                    p_bar.progress(30 + (i + 1) * 7)
                    status_text.text(f"Polling GET /api/session/{session_id} (Attempt {i+1}/10)...")
                    time.sleep(0.5)

                s_ok, s_data, s_err = api_client.get_session(session_id)
                if s_ok and s_data:
                    SessionManager.set_session(s_data)
                    st.success("Verification data received from live backend! Redirecting to Agent Workspace...")
                else:
                    st.warning("Backend pipeline still executing in background. Session state preserved.")
            else:
                p_bar.progress(100)
                status_text.text("Backend offline.")
                st.markdown(
                    f"""
                    <div style="color: #CBD5E1; font-size: 0.88rem; margin-top: 8px;">
                        The verification backend at <code>{backend_url}</code> is currently offline. 
                        Parameters for this candidate and resume have been staged in session state.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)
            st.session_state["current_page"] = "Agent Workspace"
            st.rerun()
