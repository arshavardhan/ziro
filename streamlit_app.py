"""Streamlit Community Cloud entry point alias."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Delegate directly to app.py
with open(os.path.join(ROOT_DIR, "app.py"), "r", encoding="utf-8") as f:
    exec(f.read(), globals())
