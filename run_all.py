"""
run_all.py
Launches the FastAPI backend (main.py) and Streamlit frontend (app.py)
together with one command:  python run_all.py
Press Ctrl+C to stop both.
"""

import os
import subprocess
import sys
import time

FASTAPI_PORT = os.getenv("FASTAPI_PORT", "8000")
STREAMLIT_PORT = os.getenv("STREAMLIT_PORT", "8502")


def main():
    # Detect local virtual environment python
    python_exe = sys.executable
    if os.name == "nt":
        venv_python = os.path.join("venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join("venv", "bin", "python")

    if os.path.exists(venv_python):
        python_exe = venv_python
        print(f"[run_all] Using virtual environment python: {python_exe}")
    else:
        print(f"[run_all] Using system python: {python_exe}")

    backend = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--reload", "--port", FASTAPI_PORT]
    )
    print(f"[run_all] FastAPI backend starting on http://127.0.0.1:{FASTAPI_PORT}")
    time.sleep(2)  # give the backend a moment to bind before the frontend tries to call it

    frontend = subprocess.Popen(
        [python_exe, "-m", "streamlit", "run", "app.py", "--server.port", STREAMLIT_PORT]
    )
    print(f"[run_all] Streamlit frontend starting on http://127.0.0.1:{STREAMLIT_PORT}")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\n[run_all] Shutting down...")
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(backend.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            backend.terminate()
            frontend.terminate()


if __name__ == "__main__":
    main()
