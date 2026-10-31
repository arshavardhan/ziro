"""SkillProof AI (Ziro) — Master Streamlit Application Launcher.

Production-grade entry point for Streamlit Community Cloud and local deployment.
Ensures sys.path resolution and boots the embedded verification engine automatically if needed.
"""
import os
import sys
import time
import socket
import logging
import subprocess
import atexit

# Set up root paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "skillproof", "frontend")
BACKEND_DIR = os.path.join(ROOT_DIR, "skillproof", "backend")

# Ensure FRONTEND_DIR is at sys.path[0] so frontend components and config resolve first
if BACKEND_DIR in sys.path:
    sys.path.remove(BACKEND_DIR)
if ROOT_DIR in sys.path:
    sys.path.remove(ROOT_DIR)
skillproof_dir = os.path.join(ROOT_DIR, "skillproof")
if skillproof_dir in sys.path:
    sys.path.remove(skillproof_dir)

if FRONTEND_DIR in sys.path:
    sys.path.remove(FRONTEND_DIR)
sys.path.insert(0, FRONTEND_DIR)

# Helper to check if a port is in use
def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

_backend_process = None

# Auto-boot embedded backend daemon on Streamlit Community Cloud or local standalone
def ensure_backend_running(port: int = 8001):
    global _backend_process
    if is_port_in_use(port) or is_port_in_use(8000):
        return

    try:
        env = os.environ.copy()
        deps_dir = os.path.join(BACKEND_DIR, ".deps")
        if os.path.exists(deps_dir):
            env["PYTHONPATH"] = deps_dir + os.pathsep + env.get("PYTHONPATH", "")

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ]
        _backend_process = subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def cleanup():
            global _backend_process
            if _backend_process and _backend_process.poll() is None:
                try:
                    _backend_process.terminate()
                except Exception:
                    pass

        atexit.register(cleanup)

        # Wait up to 10 seconds for backend to become available
        for _ in range(50):
            if is_port_in_use(port):
                break
            time.sleep(0.2)
    except Exception as e:
        logging.error(f"Embedded backend startup failed: {e}")

# Ensure backend daemon is active
ensure_backend_running(8001)

# Execute the master frontend app
master_frontend_app = os.path.join(FRONTEND_DIR, "app.py")
if os.path.exists(master_frontend_app):
    with open(master_frontend_app, "r", encoding="utf-8") as f:
        exec(f.read(), globals())
else:
    import streamlit as st
    st.error(f"Frontend file not found at {master_frontend_app}")
