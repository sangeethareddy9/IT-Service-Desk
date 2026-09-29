"""Cross-platform setup: py scripts/setup.py --demo (Windows)."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
ENV = BACKEND / '.venv'
PYTHON = ENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main():
    parser = argparse.ArgumentParser(description='Set up IT Service Desk locally.')
    parser.add_argument('--demo', action='store_true', help='Seed sample data into an empty database.')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10 or newer is required; Python 3.12 is recommended.')
    if not PYTHON.exists():
        print('Creating an isolated Python environment...', flush=True)
        venv.create(ENV, with_pip=True)
    print('Installing backend dependencies (internet required)...', flush=True)
    subprocess.run([str(PYTHON), '-m', 'pip', 'install', '-r', str(BACKEND / 'requirements.txt')], check=True)
    if not (BACKEND / '.env').exists():
        shutil.copyfile(BACKEND / '.env.example', BACKEND / '.env')
    subprocess.run([str(PYTHON), '-m', 'flask', '--app', 'app', 'init-db'], cwd=BACKEND, check=True)
    if args.demo:
        subprocess.run([str(PYTHON), '-m', 'flask', '--app', 'app', 'seed-demo'], cwd=BACKEND, check=True)
    print('\nSetup complete. Run: py scripts/start.py (Windows) or python3 scripts/start.py (Linux/macOS).')
    if not args.demo:
        print('Create an admin first: .venv/Scripts/python.exe -m flask --app app create-admin (from backend on Windows).')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f'Setup stopped with exit code {error.returncode}. Read the error above; existing data was not deleted.')
