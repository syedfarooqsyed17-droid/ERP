import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue

# Global in-memory event buffer queue
event_queue = Queue()

class WardenBridgeHandler(BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/v1/poll':
            # Collect all currently queued events
            events = []
            while not event_queue.empty():
                events.append(event_queue.get())
            
            res_body = json.dumps({"status": "active", "events": events}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(res_body)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(res_body)
            return
        
        # Serve frontend interface on root or HTML requests
        if self.path == '/' or self.path == '/index.html' or self.path == '/interface.html':
            try:
                filename = 'interface.html' if os.path.exists('interface.html') else 'index.html'
                if not os.path.exists(filename) and os.path.exists('frontend/interface.html'):
                    filename = 'frontend/interface.html'
                
                if os.path.exists(filename):
                    with open(filename, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(len(content)))
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(content)
                    return
            except Exception as e:
                self.send_error(500, f"Internal Server Error: {str(e)}")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == '/api/v1/crash-trigger':
            length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(length) if length > 0 else b'{}'
            try:
                data = json.loads(post_data.decode('utf-8'))
            except Exception:
                data = {}

            crash_event = {
                "type": "EXPLOIT_INTERCEPTED",
                "typeClass": data.get("typeClass", "DOM_MEMORY_LEAK_OVERLOAD"),
                "cwe": data.get("cwe", "CWE-400"),
                "path": data.get("path", "Frontend/interface.jsx"),
                "payload": data.get("payload", "UNPAGINATED_DOM_STREAM_ACTIVE"),
                "vulnCode": data.get("vulnCode", "function renderTable() {\n  for(let i=0; i<90000; i++) {\n    document.body.appendChild(createRow(i));\n  }\n}"),
                "patchedCode": data.get("patchedCode", "function renderTable() {\n  const visibleRows = items.slice(page * pageSize, (page + 1) * pageSize);\n  visibleRows.forEach(row => renderRow(row));\n}")
            }
            event_queue.put(crash_event)

            res_body = json.dumps({"status": "success", "message": "Crash event queued"}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(res_body)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(res_body)
            return

        self.send_error(404, "Endpoint not found")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), WardenBridgeHandler)
    print(f"Warden server started on port {port}")
    server.serve_forever()