"""
Production WSGI Entry Point for ContextGuard using Waitress.
Usage:
    python wsgi.py
"""
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from web.app import app
from contextguard.config import PORT
from waitress import serve

if __name__ == "__main__":
    print(f"Serving ContextGuard with Waitress WSGI on http://0.0.0.0:{PORT}")
    serve(app, host="0.0.0.0", port=PORT, threads=6)
