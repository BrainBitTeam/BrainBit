# ZCU102 Dashboard Deployment Guide

## Prerequisites

**On your development PC:**
- Node.js 18+ installed
- npm installed

**On ZCU102:**
- Linux running on A53
- Python 3 installed
- Network connectivity

## Step 1: Build on Development PC

```bash
cd radio-scribe-studio-main

# Install dependencies (first time only)
npm install

# Build production bundle
npm run build
```

This creates a `dist/` folder with the optimized dashboard.

## Step 2: Transfer to ZCU102

Copy these files to the ZCU102:

```bash
# Using scp (adjust IP and path as needed)
scp -r dist/ root@<ZCU102_IP>:/opt/dashboard/
scp zcu102_server.py root@<ZCU102_IP>:/opt/dashboard/
scp start_dashboard.sh root@<ZCU102_IP>:/opt/dashboard/
```

## Step 3: Create radio_state.json

On the ZCU102, create `/radio_state.json`:

```bash
cat > /radio_state.json << 'EOF'
{
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
  "rx_only": false,
  "led_on": false,
  "gps_on": false,
  "members": []
}
EOF
```

## Step 4: Start the Dashboard

```bash
cd /opt/dashboard
chmod +x start_dashboard.sh
./start_dashboard.sh
```

Or run directly:
```bash
python3 /opt/dashboard/zcu102_server.py --port 8080 --json-path /radio_state.json
```

## Step 5: Access the Dashboard

Open a browser and navigate to:
```
http://<ZCU102_IP>:8080
```

## Auto-start on Boot (Optional)

Create a systemd service:

```bash
cat > /etc/systemd/system/dashboard.service << 'EOF'
[Unit]
Description=BrainBit Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/dashboard
ExecStart=/usr/bin/python3 /opt/dashboard/zcu102_server.py --port 8080 --json-path /radio_state.json
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dashboard
systemctl start dashboard
```

## Updating radio_state.json

Your radio application should update `/radio_state.json` directly. The dashboard polls this file every 500ms.

Example from Python:
```python
import json

def update_radio_state(updates):
    with open('/radio_state.json', 'r') as f:
        state = json.load(f)
    state.update(updates)
    with open('/radio_state.json', 'w') as f:
        json.dump(state, f, indent=2)

# Example: update frequency
update_radio_state({"frequency_hz": 450000000.0})
```

## Troubleshooting

**Dashboard not loading:**
- Check if `dist/` folder exists and contains `index.html`
- Verify Python 3 is installed: `python3 --version`
- Check firewall allows port 8080

**JSON file not found:**
- Ensure `/radio_state.json` exists and is readable
- Check file permissions: `chmod 644 /radio_state.json`

**Slow performance:**
- The A53 is sufficient for this dashboard
- Reduce polling interval in `src/config/dashboard.ts` if needed

## File Structure on ZCU102

```
/opt/dashboard/
├── dist/                  # Built React files
│   ├── index.html
│   └── assets/
├── zcu102_server.py       # Python server
└── start_dashboard.sh     # Startup script

/radio_state.json          # Radio state file (root)
```
