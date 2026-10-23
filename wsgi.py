"""
Production WSGI Entry Point for ContextGuard using Waitress.
Reads PORT from environment variable (required for Render, Railway, Heroku).

Usage:
    python wsgi.py
"""
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from web.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    threads = int(os.environ.get("WSGI_THREADS", "6"))

    print(f"ContextGuard Dashboard running at http://{host}:{port}")

    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=threads)
    except ImportError:
        # Fallback to Flask dev server if waitress not installed
        print("[Warning] waitress not found, falling back to Flask dev server.")
        app.run(host=host, port=port, debug=False)
