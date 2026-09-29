"""Run the bundled frontend and backend together using Waitress on localhost."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / 'backend' / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def open_when_ready(process):
    for _ in range(30):
        if process.poll() is not None:
            return
        try:
            with urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open('http://127.0.0.1:5000')
                    return
        except OSError:
            time.sleep(0.5)


if __name__ == '__main__':
    if not PYTHON.exists():
        sys.exit('Run py scripts/setup.py --demo first (python3 on Linux/macOS).')
    if not (ROOT / 'frontend' / 'dist' / 'index.html').exists():
        sys.exit('Frontend build is missing. Run npm ci, then npm run build in frontend/.')
    print('DeskFlow: http://127.0.0.1:5000 — leave this window open. Ctrl+C stops the server.', flush=True)
    process = subprocess.Popen([str(PYTHON), '-m', 'waitress', '--listen=127.0.0.1:5000', 'app:app'], cwd=ROOT / 'backend')
    threading.Thread(target=open_when_ready, args=(process,), daemon=True).start()
    try:
        sys.exit(process.wait())
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
