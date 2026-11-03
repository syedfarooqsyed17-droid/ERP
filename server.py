import json
import os
import queue
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Central queue holding telemetry events for polling delivery
event_queue = queue.Queue(maxsize=100)


class NexusTelemetryHandler(SimpleHTTPRequestHandler):

    def _send_cors(self):
        """Inject strict cross-origin headers to allow Warden access."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE"
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Requested-With",
        )

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200, "OK")
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        # Health check endpoint for Render keep-alive monitoring
        if self.path == "/health":
            body = json.dumps({"status": "healthy"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(body)
            return

        # HTTP Polling endpoint for Warden dashboard to fetch live telemetry instantly
        if self.path == "/api/v1/poll":
            events = []
            while not event_queue.empty():
                try:
                    events.append(event_queue.get_nowait())
                except queue.Empty:
                    break

            body = json.dumps({"events": events}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(body)
            return

        # Track and log standard web traffic requests
        if not self.path.startswith("/api/v1/"):
            event_queue.put(
                {
                    "type": "TRAFFIC",
                    "method": "GET",
                    "status": 200,
                    "route": self.path,
                    "client": (
                        self.client_address[0]
                        if self.client_address
                        else "127.0.0.1"
                    ),
                }
            )

        return super().do_GET()

    def do_POST(self):
        # Handle incoming exploit or crash trigger telemetry
        if self.path == "/api/v1/crash-trigger":
            length = int(self.headers.get("Content-Length", 0))
            post_data = (
                self.rfile.read(length) if length > 0 else b"{}"
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
                        " i++) {\n    document.body.appendChild(createRow(i));\n"
                        "  }\n}"
                    ),
                ),
                "patchedCode": data.get(
                    "patchedCode",
                    (
                        "function renderTable() {\n  // Virtualized Windowing"
                        " Pagination\n  const visibleRows = items.slice(page *"
                        " pageSize, (page + 1) * pageSize);\n"
                        "  visibleRows.forEach(row => renderRow(row));\n}"
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
            self._send_cors()
            self.end_headers()
            self.wfile.write(res_body)
            return

        self.send_error(404, "Endpoint not found")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    server = HTTPServer(("0.0.0.0", port), NexusTelemetryHandler)
    print(f"NEXUS ERP & CRM Enterprise Platform running on port {port}...")
    server.serve_forever()