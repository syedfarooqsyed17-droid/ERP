import http.server
import json
import os
import queue
import socketserver
import sys
import time
import webbrowser

PORT = 8001
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
JSX_PATH = os.path.join(DIRECTORY, "Frontend", "interface.jsx")
HTML_PATH = os.path.join(DIRECTORY, "index.html")

_last_jsx_mtime = 0

# Telemetry event queue for Warden SSE stream
event_queue = queue.Queue()


def check_and_rebuild_if_needed():
    global _last_jsx_mtime
    try:
        if os.path.exists(JSX_PATH):
            mtime = os.path.getmtime(JSX_PATH)
            if mtime > _last_jsx_mtime:
                from build_dist import build

                build()
                _last_jsx_mtime = mtime
    except Exception as e:
        print(f"Auto-build warning: {e}")


class ERPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight requests for telemetry endpoints."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        """Handle incoming telemetry crash triggers from clients or remote nodes."""
        check_and_rebuild_if_needed()

        if self.path == "/api/v1/crash-trigger":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

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
                        "function renderTable() {\n  for(let i=0; i<90000; i++) {\n"
                        "    document.body.appendChild(createRow(i));\n  }\n}"
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

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = {"status": "success", "message": "Crash event queued for AST patch"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        self.send_error(404, "Endpoint not found")

    def do_GET(self):
        check_and_rebuild_if_needed()

        # Handle Health Check endpoint for Primary Watchdog monitoring
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            health_data = {"status": "healthy", "timestamp": time.time()}
            self.wfile.write(json.dumps(health_data).encode("utf-8"))
            return

        # Handle Warden SSE Telemetry Stream
        if self.path == "/api/v1/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Keep SSE stream open and send initial keep-alive
            try:
                self.wfile.write(b": keep-alive\n\n")
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
            except (ConnectionResetError, BrokenPipeError):
                return
            return

        # Handle favicon without 404
        if self.path == "/favicon.ico":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            svg_icon = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">&#127970;</text></svg>'
            self.wfile.write(svg_icon)
            return

        # Default root '/' or '/Frontend/' to index.html
        if self.path in ("/", "", "/Frontend", "/Frontend/"):
            self.path = "/index.html"

        # Intercept and log standard traffic telemetry
        if not self.path.startswith("/api/v1/"):
            log_event = {
                "type": "TRAFFIC",
                "method": "GET",
                "status": 200,
                "route": self.path,
                "client": self.client_address[0],
                "latency": "1.2",
            }
            event_queue.put(log_event)

        return super().do_GET()

    def end_headers(self):
        # Enable CORS and caching headers for smooth ES module and asset loading
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


def run_server():
    os.chdir(DIRECTORY)
    check_and_rebuild_if_needed()
    handler = ERPRequestHandler

    port = PORT
    for attempt in range(20):
        try:
            # Bind explicitly to "0.0.0.0" so secondary laptop accepts Wi-Fi traffic
            with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
                url = f"http://localhost:{port}"
                print("=" * 65)
                print(" NEXUS ERP & CRM Enterprise Platform")
                print(" Status: SERVER ACTIVE & RUNNING ON ALL INTERFACES (0.0.0.0)")
                print(f" Local Web Interface: {url}")
                print(f" Serving Directory: {DIRECTORY}")
                print(
                    " Press Ctrl+C in this terminal to shut down the server."
                )
                print("=" * 65)
                sys.stdout.flush()

                try:
                    webbrowser.open(url)
                except Exception as e:
                    print(
                        f"Note: Could not automatically open browser ({e})."
                    )
                    sys.stdout.flush()

                httpd.serve_forever()
                break
        except OSError as e:
            if "Address already in use" in str(e) or getattr(
                e, "errno", 0
            ) in (10048, 98):
                port += 1
                continue
            else:
                print(f"Server error: {e}")
                sys.stdout.flush()
                raise e


if __name__ == "__main__":
    run_server()