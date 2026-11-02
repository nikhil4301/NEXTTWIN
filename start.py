#!/usr/bin/env python3
"""
NextTwin - One-command launcher
Starts: Python API server (port 8000) + Frontend static server (port 3000)
"""
import subprocess
import sys
import os
import threading
import time
import http.server

BACKEND_PORT = int(os.environ.get("PORT", 8000))
FRONTEND_PORT = 3000

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")


def run_backend():
    print(f"[API] Starting Python backend on port {BACKEND_PORT}...")
    subprocess.run([sys.executable, os.path.join(BACKEND_DIR, "server.py")], cwd=BACKEND_DIR)


def run_frontend():
    time.sleep(1)
    print(f"[UI]  Serving frontend on http://localhost:{FRONTEND_PORT}")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_GET(self):
            filepath = os.path.join(FRONTEND_DIR, "index.html")
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())

    server = http.server.HTTPServer(("0.0.0.0", FRONTEND_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    print("=" * 55)
    print("  🧬 NextTwin — Digital Academic Twin")
    print("=" * 55)
    print(f"  Backend API  →  http://localhost:{BACKEND_PORT}/api")
    print(f"  Frontend App →  http://localhost:{FRONTEND_PORT}")
    print("=" * 55)
    print("  Tech Stack:")
    print("   • Python (http.server + sqlite3 stdlib)")
    print("   • SQL (SQLite3 database)")
    print("   • JavaScript (React 18 + Recharts)")
    print("=" * 55)

    t1 = threading.Thread(target=run_frontend, daemon=True)
    t1.start()
    run_backend()
