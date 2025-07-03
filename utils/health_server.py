"""
Health check server for deployment platforms.
Provides a simple HTTP endpoint for health checks.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that always responds 200 OK."""
    
    def do_GET(self):
        # Always respond 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")


def run_health_server():
    """Start the health check server in a separate thread."""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    # This will block forever handling health-check requests
    server.serve_forever()


def start_health_server():
    """Start the health check server in a daemon thread."""
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health check server started.")
    return health_thread 