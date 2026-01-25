#!/bin/bash
# ZCU102 Dashboard Startup Script
# Run this script on the ZCU102 to start the dashboard server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JSON_PATH="/radio_state.json"
PORT=8080

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --json-path)
            JSON_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--port 8080] [--json-path /radio_state.json]"
            exit 1
            ;;
    esac
done

echo "Starting BrainBit Dashboard..."
echo "  Port: $PORT"
echo "  JSON Path: $JSON_PATH"

cd "$SCRIPT_DIR"
python3 zcu102_server.py --port "$PORT" --json-path "$JSON_PATH"
