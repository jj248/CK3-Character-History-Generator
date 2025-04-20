# launcher.py
import subprocess
import os
import sys

def run_streamlit_app():
    app_path = os.path.join(os.path.dirname(__file__), "ui_app.py")
    subprocess.Popen(["streamlit", "run", app_path])

if __name__ == "__main__":
    run_streamlit_app()