#!/usr/bin/env python3
"""
Lightweight dashboard server for ZCU102 A53 Linux
Serves the React dashboard and handles radio_state.json API

Usage:
    python3 zcu102_server.py [--port 8080] [--json-path /radio_state.json]
"""

import http.server
import socketserver
import json
import os
import argparse
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Configuration
DEFAULT_PORT = 8080
DEFAULT_JSON_PATH = "/radio_state.json"
STATIC_DIR = Path(__file__).parent / "dist"


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for dashboard with JSON API support"""

    json_path = DEFAULT_JSON_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Handle radio status API
        if path == "/api/radio-status.json":
            self.handle_get_radio_status()
            return

        # Handle voice activity API (if exists)
        if path == "/api/voice-activity.json":
            self.handle_get_voice_activity()
            return

        # For SPA routing: serve index.html for non-file routes
        file_path = STATIC_DIR / path.lstrip("/")
        if not file_path.exists() and not path.startswith("/assets"):
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/radio-status.json":
            self.handle_post_radio_status()
            return

        self.send_error(404, "Not Found")

    def handle_get_radio_status(self):
        """Read and return radio_state.json"""
        try:
            with open(self.json_path, "r") as f:
                data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        except FileNotFoundError:
            self.send_json_error(404, f"File not found: {self.json_path}")
        except Exception as e:
            self.send_json_error(500, f"Error reading file: {str(e)}")

    def handle_get_voice_activity(self):
        """Return voice activity status (placeholder or from file)"""
        voice_path = Path(self.json_path).parent / "voice_activity.json"

        try:
            if voice_path.exists():
                with open(voice_path, "r") as f:
                    data = f.read()
            else:
                # Default voice activity state
                data = json.dumps({
                    "isUserSpeaking": False,
                    "isModelSpeaking": False,
                    "userTranscript": "",
                    "modelResponse": ""
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        except Exception as e:
            self.send_json_error(500, f"Error: {str(e)}")

    def handle_post_radio_status(self):
        """Update radio_state.json with merged data"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            new_data = json.loads(body)

            # Read existing and merge
            existing_data = {}
            if os.path.exists(self.json_path):
                with open(self.json_path, "r") as f:
                    existing_data = json.load(f)

            merged_data = {**existing_data, **new_data}

            with open(self.json_path, "w") as f:
                json.dump(merged_data, f, indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        except json.JSONDecodeError as e:
            self.send_json_error(400, f"Invalid JSON: {str(e)}")
        except Exception as e:
            self.send_json_error(500, f"Error updating file: {str(e)}")

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json_error(self, code, message):
        """Send JSON error response"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

    def log_message(self, format, *args):
        """Custom logging - reduce noise for polling"""
        if "/api/" not in args[0]:  # Don't log API polls
            print(f"[{self.log_date_time_string()}] {args[0]}")


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCP server for concurrent connections"""
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description="ZCU102 Dashboard Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--json-path", default=DEFAULT_JSON_PATH, help="Path to radio_state.json")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    # Set the JSON path for the handler
    DashboardHandler.json_path = args.json_path

    # Check if dist directory exists
    if not STATIC_DIR.exists():
        print(f"Error: Build directory not found at {STATIC_DIR}")
        print("Run 'npm run build' first to create the production build")
        return 1

    # Check if JSON file exists
    if not os.path.exists(args.json_path):
        print(f"Warning: {args.json_path} not found. Creating default...")
        default_state = {
            "frequency_hz": 300000000.0,
            "bandwidth_hz": 25000,
            "waveform": "NB",
            "modulation": "QAM16",
            "power_level": "high",
            "battery_percent": 100,
            "battery_voltage": 12.6,
            "errors": [],
            "channel": 1,
            "volume": 5,
            "rx_only": False,
            "led_on": False,
            "gps_on": False,
            "members": []
        }
        with open(args.json_path, "w") as f:
            json.dump(default_state, f, indent=2)

    with ThreadedServer((args.host, args.port), DashboardHandler) as httpd:
        print(f"Dashboard server running at http://{args.host}:{args.port}")
        print(f"Reading radio state from: {args.json_path}")
        print(f"Serving static files from: {STATIC_DIR}")
        print("Press Ctrl+C to stop")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()

    return 0


if __name__ == "__main__":
    exit(main())
