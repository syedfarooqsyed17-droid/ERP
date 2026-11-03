from server import ERPRequestHandler, DIRECTORY
import http.server
import socketserver

# Expose handler as application for WSGI/Gunicorn servers if needed, 
# or run a custom HTTP server runner.
app = ERPRequestHandler