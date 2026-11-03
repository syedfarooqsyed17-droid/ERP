import json
import os
import queue
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Central queue holding telemetry events for SSE delivery
event_queue = queue.Queue()


class NexusShieldHandler(SimpleHTTPRequestHandler):

    def _send_cors_headers(self):
        """Inject strict cross-origin headers to prevent browser drops."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE"
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Requested-With",
        )

    def do_OPTIONS(self):
        """Handle CORS preflight requests from cross-origin dashboards."""
        self.send_response(200, "OK")
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Health check endpoint for Render service keep-alive
        if self.path == "/health":
            body = json.dumps({"status": "healthy"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        # Real-time SSE Telemetry Ingress Endpoint
        if self.path == "/api/v1/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self._send_cors_headers()
            self.end_headers()

            try:
                # Immediate stream heartbeat open chunk
                self.wfile.write(b": open\n\n")
                self.wfile.flush()

                while True:
                    try:
                        event_data = event_queue.get(timeout=10)
                        msg = f"data: {json.dumps(event_data)}\n\n"
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
            except (ConnectionResetError, BrokenPipeError, SocketError):
                return
            return

        # Handle standard incoming app routes & log telemetry
        log_event = {
            "type": "TRAFFIC",
            "method": "GET",
            "status": 200,
            "route": self.path,
            "client": self.client_address[0] if self.client_address else "127.0.0.1",
        }
        event_queue.put(log_event)

        # Standard file fallback or 200 response
        return super().do_GET()

    def do_POST(self):
        # Crash telemetry ingress from frontend DOM exploits
        if self.path == "/api/v1/crash-trigger":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = (
                self.rfile.read(content_length) if content_length > 0 else b"{}"
            )

            try:
                data = json.loads(post_data.decode("utf-8"))
            except Exception:
                data = {}

            crash_event = {
                "type": "EXPLOIT_INTERCEPTED",
                "typeClass": data.get("typeClass", "DOM_MEMORY_LEAK_OVERLOAD"),
                "cwe": data.get("cwe", "CWE-400"),
                "path": data.get("path", "Frontend/interface.jsx"),
                "payload": data.get("payload", "UNPAGINATED_DOM_STREAM_ACTIVE"),
                "vulnCode": data.get(
                    "vulnCode",
                    (
                        "function renderTable() {\n  for(let i=0; i<90000;"
                        " i++) {\n   "
                        " document.body.appendChild(createRow(i));\n  }\n}"
                    ),
                ),
                "patchedCode": data.get(
                    "patchedCode",
                    (
                        "function renderTable() {\n  // Virtualized Windowing"
                        " Pagination\n  const visibleRows = items.slice(page *"
                        " pageSize, (page + 1) * pageSize);\n "
                        " visibleRows.forEach(row => renderRow(row));\n}"
                    ),
                ),
            }

            event_queue.put(crash_event)

            res_body = json.dumps(
                {"status": "success", "message": "Crash event queued"}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(res_body)
            return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    server = HTTPServer(("0.0.0.0", port), NexusShieldHandler)
    print(f"NEXUS ERP Target Web App running on port {port}...")
    server.serve_forever()