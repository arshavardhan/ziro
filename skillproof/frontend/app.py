import os
import sys
import streamlit as st

# Ensure skillproof/frontend directory is at the top of sys.path
frontend_dir = os.path.dirname(os.path.abspath(__file__))
if frontend_dir in sys.path:
    sys.path.remove(frontend_dir)
sys.path.insert(0, frontend_dir)

from config import APP_ICON, APP_NAME
from services.session_manager import SessionManager
from components.sidebar import render_sidebar
import pages.overview as p_overview
import pages.verification as p_verification
import pages.agent_workspace as p_agent_workspace
import pages.repository_intelligence as p_repo_intel
import pages.evidence_explorer as p_evidence
import pages.git_forensics as p_git
import pages.originality as p_orig
import pages.skill_assessment as p_skills
import pages.technical_viva as p_viva
import pages.reviewer_approval as p_approval
import pages.credentials as p_credentials
import pages.evaluation_lab as p_eval

# Configure Streamlit Page
st.set_page_config(
    page_title=f"{APP_NAME} — Enterprise Verification",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load External CSS System
css_path = os.path.join(frontend_dir, "assets", "styles.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize Session State
SessionManager.init_session()

# Render Navigation Sidebar
current_page = render_sidebar()

# Page Routing to 12 Sub-Systems
if current_page == "Overview":
    p_overview.render()
elif current_page == "Candidate Verification":
    p_verification.render()
elif current_page == "Agent Workspace":
    p_agent_workspace.render()
elif current_page == "Repository Intelligence":
    p_repo_intel.render()
elif current_page == "Evidence Explorer":
    p_evidence.render()
elif current_page == "Git Forensics":
    p_git.render()
elif current_page == "Originality Analysis":
    p_orig.render()
elif current_page == "Skill Assessment":
    p_skills.render()
elif current_page == "Technical Viva":
    p_viva.render()
elif current_page == "Reviewer Approval":
    p_approval.render()
elif current_page == "Credentials":
    p_credentials.render()
elif current_page == "Evaluation Lab":
    p_eval.render()
else:
    p_overview.render()
