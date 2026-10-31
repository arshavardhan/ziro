import os
import json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'outputs'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA / 'skillproof.sqlite3'
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini')
LLM_BASE_URL = os.getenv('LLM_BASE_URL') or ('https://generativelanguage.googleapis.com/v1beta/openai' if LLM_PROVIDER == 'gemini' else 'https://api.openai.com/v1')
LLM_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('LLM_API_KEY', '')
LLM_MODEL = os.getenv('GEMINI_MODEL') or os.getenv('LLM_MODEL', 'gemini-3.5-flash-lite' if LLM_PROVIDER == 'gemini' else 'gpt-4.1-mini')
EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'gemini')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'gemini-embedding-001')
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
ORCHESTRATOR_ENGINE = os.getenv('ORCHESTRATOR_ENGINE', 'langgraph')
ANALYZER_VERSION = '2.1.0'
CONFIG_VERSION = '2026-10-reliability-1'
AGENT_BUDGET_SECONDS = int(os.getenv('AGENT_BUDGET_SECONDS', '600'))
LLM_TIMEOUT_SECONDS = float(os.getenv('LLM_TIMEOUT_SECONDS', '60'))
SCORE_WEIGHTS = json.loads(os.getenv('SCORE_WEIGHTS', '{"implementation_score":30,"test_score":20,"architecture_score":15,"git_score":10,"viva_score":25}'))
if set(SCORE_WEIGHTS) != {'implementation_score','test_score','architecture_score','git_score','viva_score'} or any(not isinstance(v,(int,float)) or v<0 for v in SCORE_WEIGHTS.values()) or sum(SCORE_WEIGHTS.values()) != 100:
    raise ValueError('SCORE_WEIGHTS must contain the five supported factors and sum to 100')
SIGNING_SECRET = os.getenv('SIGNING_SECRET', '')
REVIEWER_TOKEN = os.getenv('REVIEWER_TOKEN', '')
MAX_REPO_BYTES = 50 * 1024 * 1024
MAX_CLONE_BYTES = int(os.getenv('MAX_CLONE_MB', '150')) * 1024 * 1024
WORKSPACES = ROOT / 'workspaces'
WORKSPACES.mkdir(exist_ok=True)
CREDENTIALS = ROOT / 'credentials'
CREDENTIALS.mkdir(exist_ok=True)
CORS_ORIGINS = [v.strip() for v in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if v.strip()]
MAX_FILES = 500
MAX_CYCLES = 3
VIVA_COUNT = 5
MAX_FILE_BYTES = 100_000
MIN_SCORE = float(os.getenv('MIN_SCORE', '65'))
MIN_VIVA = float(os.getenv('MIN_VIVA', '60'))
TEST_IMAGE = os.getenv('TEST_IMAGE', 'skillproof-tests:local')
