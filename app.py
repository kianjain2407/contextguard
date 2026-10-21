"""
ContextGuard Web Dashboard Entry Point.
Usage:
    python app.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from web.app import app
from contextguard.config import PORT, DEBUG

if __name__ == "__main__":
    print(f"ContextGuard Dashboard running at http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=DEBUG)
