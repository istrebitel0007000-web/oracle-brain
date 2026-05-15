"""
app.py — Entry point for Gunicorn / Render deployment
Usage:
  Development:  python app.py
  Production:   gunicorn app:app --worker-class gevent --workers 2 --bind 0.0.0.0:$PORT
"""
from __future__ import annotations

import os
import sys

from oracle_brain import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "production") != "production"
    print(f"Starting Oracle Brain on port {port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
