import uvicorn
import os
import sys
import webbrowser
import threading
import time

# Add the current directory to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def open_browser():
    """Wait for server to start then open browser"""
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8081")

if __name__ == "__main__":
    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run server
    # workers=1 is important for PyInstaller
    # reload=False is important for frozen app
    uvicorn.run("app.main:app", host="127.0.0.1", port=8081, reload=False, workers=1)
