from __future__ import annotations
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/extract":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size) or b"{}")
        if payload.get("schema_version") == "2.0":
            response = {"records": [{"code": value, "result": "unknown"} for value in payload.get("courses", [])]}
        else:
            response = {"courses": [{"course_code": value, "grade": "A"} for value in payload.get("courses", [])]}
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format, *_args):
        return

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("MOCK_SIS_PORT", "8020"))), Handler).serve_forever()
