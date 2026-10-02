import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_MARKER = VENV / ".requirements-sha256"


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    if not PYTHON.is_file():
        run([sys.executable, "-m", "venv", str(VENV)])

    requirements_hash = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    installed_hash = REQUIREMENTS_MARKER.read_text().strip() if REQUIREMENTS_MARKER.exists() else ""
    if installed_hash != requirements_hash:
        run([str(PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        REQUIREMENTS_MARKER.write_text(requirements_hash + "\n", encoding="ascii")

    browser_path = subprocess.run(
        [str(PYTHON), "-c", "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not Path(browser_path).is_file():
        run([str(PYTHON), "-m", "playwright", "install", "chromium"])

    result = subprocess.run([str(PYTHON), str(ROOT / "collector.py"), *sys.argv[1:]], cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()