#!/usr/bin/env python3
"""
Lightweight HTTP server that runs on the HOST to trigger Instagram sync.

The Instagram sync must run from the host (not Docker) because session cookies
are IP-bound to the host machine's residential IP.

Usage:
    python scripts/sync_server.py          # Start on port 8002
    python scripts/sync_server.py --port 8003

The frontend calls this server directly from the browser (which also runs on the host).
"""
import argparse
import json
import subprocess
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SYNC_SCRIPT = PROJECT_ROOT / "scripts" / "ig_sync.py"


class SyncHandler(BaseHTTPRequestHandler):
    # Track running sync
    _sync_lock = threading.Lock()
    _sync_running = False
    _last_result = None

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            self._json_response(200, {
                "running": SyncHandler._sync_running,
                "last_result": SyncHandler._last_result,
            })
        elif self.path == "/health":
            self._json_response(200, {"status": "ok"})
        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/sync":
            self._handle_sync()
        else:
            self._json_response(404, {"error": "Not found"})

    def _handle_sync(self):
        with SyncHandler._sync_lock:
            if SyncHandler._sync_running:
                self._json_response(409, {"error": "Sync already in progress"})
                return
            SyncHandler._sync_running = True
            SyncHandler._last_result = None

        # Send immediate response
        self._json_response(202, {"status": "sync_started"})

        # Run sync in background thread
        thread = threading.Thread(target=self._run_sync, daemon=True)
        thread.start()

    def _run_sync(self):
        try:
            result = subprocess.run(
                [sys.executable, str(SYNC_SCRIPT)],
                capture_output=True,
                text=True,
                timeout=600,  # 10 min max
                cwd=str(PROJECT_ROOT),
                env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
            )
            SyncHandler._last_result = {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-2000:] if result.stdout else "",
                "stderr_tail": result.stderr[-1000:] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            SyncHandler._last_result = {"success": False, "error": "Sync timed out (10 min)"}
        except Exception as e:
            SyncHandler._last_result = {"success": False, "error": str(e)}
        finally:
            SyncHandler._sync_running = False

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[sync-server] {args[0]}" if args else "")


def main():
    parser = argparse.ArgumentParser(description="Instagram Sync HTTP Server")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), SyncHandler)
    print(f"[sync-server] Listening on http://localhost:{args.port}")
    print(f"[sync-server] POST /sync   — trigger Instagram sync")
    print(f"[sync-server] GET  /status  — check sync progress")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[sync-server] Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
