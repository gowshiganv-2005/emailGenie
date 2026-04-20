import uvicorn
import os
import sys
import webbrowser
from threading import Timer
from dotenv import load_dotenv

# Set the current working directory to the script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.append(SCRIPT_DIR)

# Render sets the PORT environment variable. Falls back to 8002 for local development.
PORT = int(os.environ.get("PORT", 8002))
# On Render, we must bind to 0.0.0.0. Locally, 127.0.0.1 is standard.
IS_RENDER = os.environ.get("RENDER")
HOST = "0.0.0.0" if IS_RENDER else "127.0.0.1"

def open_browser():
    """Opens the local UI in the default web browser."""
    print(f"Opening browser at http://{HOST}:{PORT}...")
    webbrowser.open(f"http://{HOST}:{PORT}")

if __name__ == "__main__":
    load_dotenv(override=True)
    
    print("\n" + "="*40)
    print(" Shuttle One - Premium Email Agent is running!")
    print(f"  URL: http://{HOST}:{PORT}")
    print("="*40 + "\n")
    
    # Only try to open the browser if we're not running on Render
    if not IS_RENDER:
        Timer(1.5, open_browser).start()    
    
    try:
        uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
    except Exception as e:
        print(f"\nERROR: Could not start the server: {e}")
        if not IS_RENDER:
            if "address already in use" in str(e).lower() or "winerror 10048" in str(e).lower():
                print(f"TIP: Port {PORT} is already being used. Try closing other running instances or change the PORT variable in run.py.")
            input("\nPress Enter to exit...")
