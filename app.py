import sys
import os

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import uvicorn
from web.server import app

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Oracle Fusion Cloud Test Automation Platform")
    print("Web UI available at: http://127.0.0.1:8000")
    print("Root Project Directory: A:\\test automation")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
