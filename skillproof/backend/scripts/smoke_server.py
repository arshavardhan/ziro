"""Start the real ASGI server, check HTTP health/OpenAPI, then stop it."""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '18000'], cwd=root)
try:
    for attempt in range(40):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18000/health', timeout=1) as response:
                assert response.status == 200
                print(response.read().decode())
            with urllib.request.urlopen('http://127.0.0.1:18000/openapi.json', timeout=1) as response:
                assert response.status == 200
            print('Real Uvicorn startup, health and OpenAPI checks passed')
            break
        except OSError:
            if process.poll() is not None:
                raise RuntimeError('Server exited before startup')
            time.sleep(.25)
    else:
        raise RuntimeError('Server startup timed out')
finally:
    process.terminate()
    process.wait(timeout=10)
