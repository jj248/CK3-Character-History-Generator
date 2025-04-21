import sys
import os
import time
import threading
import socket
import subprocess

def wait_for_server_and_open_browser(port, timeout=10):
    """Wait for Streamlit server to start before opening the browser."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                import webbrowser
                webbrowser.open(f"http://localhost:{port}")
                return
        except OSError:
            time.sleep(0.5)
    print("⚠️ Could not connect to Streamlit server after waiting.")

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

real_script = os.path.join(base_path, "interface", "ui_app.py")

# Set environment variables to suppress warnings and dev browser
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_PORT"] = "8501"
os.environ["STREAMLIT_SERVER_ADDRESS"] = "localhost"
os.environ["STREAMLIT_SERVER_ENABLECORS"] = "false"
os.environ["STREAMLIT_SERVER_ENABLEXSRFPROTECTION"] = "false"
os.environ["BROWSER"] = "none"

# Start browser opener thread
threading.Thread(target=wait_for_server_and_open_browser, args=(8501,), daemon=True).start()

# Run Streamlit via subprocess
subprocess.run(["streamlit", "run", real_script])
