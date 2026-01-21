"""
Radio TCP client for communicating with the ZCU102 target.

Provides both real TCP communication and a simulation mode for testing.
"""

import socket
import threading
import queue
import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class RadioResponse:
    """
    Response from the radio system.

    Attributes:
        success: Whether the command was processed successfully.
        message: The response message from the radio.
        is_simulated: Whether this response came from simulation.
    """
    success: bool
    message: str
    is_simulated: bool = False


class SimulatedRadio:
    """
    Simulated radio for testing without hardware.

    Maintains internal state and responds to commands similarly to the real parser.
    """

    def __init__(self):
        self._state = {
            "frequency_hz": 450e6,
            "bandwidth_hz": 1e6,
            "waveform": "WB",
            "modulation": "QAM16",
            "power_level": "medium",
            "battery_percent": 78,
            "battery_voltage": 12.60,
            "members_count": 5,
            "errors": [],
            "channel": 1,
            "volume": 5,
            "rx_only": False,
            "led_on": False,
            "gps_on": True,
        }

    def _hz_str(self, hz: float) -> str:
        """Convert Hz to human-readable string."""
        if hz >= 1e9:
            return f"{hz/1e9:.2f} GHz"
        elif hz >= 1e6:
            return f"{hz/1e6:.2f} MHz"
        elif hz >= 1e3:
            return f"{hz/1e3:.2f} kHz"
        return f"{hz:.0f} Hz"

    def process(self, command: str) -> str:
        """Process a command and return simulated response."""
        cmd_lower = command.lower()

        # Query commands
        if any(q in cmd_lower for q in ["what is", "show", "get", "check", "how many"]):
            if "frequency" in cmd_lower:
                return f"Frequency: {self._hz_str(self._state['frequency_hz'])}"
            elif "bandwidth" in cmd_lower:
                return f"Bandwidth: {self._hz_str(self._state['bandwidth_hz'])}"
            elif "waveform" in cmd_lower:
                return f"Waveform: {self._state['waveform']}"
            elif "modulation" in cmd_lower:
                return f"Modulation: {self._state['modulation']}"
            elif "power" in cmd_lower:
                return f"Power level: {self._state['power_level']}"
            elif "battery" in cmd_lower:
                return f"Battery: {self._state['battery_percent']}% at {self._state['battery_voltage']:.2f} V"
            elif "member" in cmd_lower or "network" in cmd_lower:
                return f"Members count: {self._state['members_count']}"
            elif "error" in cmd_lower:
                errors = self._state['errors']
                if not errors:
                    return "Errors: 0"
                return f"Errors ({len(errors)}): {', '.join(errors)}"
            elif "channel" in cmd_lower:
                return f"Channel: {self._state['channel']}"
            elif "volume" in cmd_lower:
                return f"Volume: {self._state['volume']}"
            elif "receive only" in cmd_lower or "rx only" in cmd_lower:
                return f"Receive only mode: {'on' if self._state['rx_only'] else 'off'}"
            elif "led" in cmd_lower:
                return f"LED: {'on' if self._state['led_on'] else 'off'}"
            elif "gps" in cmd_lower:
                return f"GPS: {'on' if self._state['gps_on'] else 'off'}"
            elif "status" in cmd_lower:
                return f"Radio status: Battery {self._state['battery_percent']}%, {len(self._state['errors'])} errors"
            elif "config" in cmd_lower or "setting" in cmd_lower:
                return (
                    f"Radio configuration: "
                    f"Frequency: {self._hz_str(self._state['frequency_hz'])}, "
                    f"Bandwidth: {self._hz_str(self._state['bandwidth_hz'])}, "
                    f"Waveform: {self._state['waveform']}, "
                    f"Modulation: {self._state['modulation']}, "
                    f"Channel: {self._state['channel']}, "
                    f"Volume: {self._state['volume']}, "
                    f"Power: {self._state['power_level']}"
                )
            elif "bit" in cmd_lower or "test" in cmd_lower:
                return "BIT status: No errors detected"

        # Control commands
        if "set" in cmd_lower or "change" in cmd_lower or "to" in cmd_lower:
            # Frequency
            if "frequency" in cmd_lower:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*(mhz|khz|ghz|hz)?', cmd_lower)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2) or "mhz"
                    multiplier = {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}.get(unit, 1e6)
                    self._state["frequency_hz"] = value * multiplier
                    return f"Frequency set to {self._hz_str(self._state['frequency_hz'])}"

            # Channel
            if "channel" in cmd_lower:
                import re
                match = re.search(r'channel.*?(\d+)', cmd_lower)
                if match:
                    ch = int(match.group(1))
                    if 1 <= ch <= 200:
                        self._state["channel"] = ch
                        return f"Channel set to {ch}"
                    return f"Invalid channel. Must be 1-200"

            # Volume
            if "volume" in cmd_lower:
                import re
                match = re.search(r'volume.*?(\d+)', cmd_lower)
                if match:
                    vol = int(match.group(1))
                    if 1 <= vol <= 10:
                        self._state["volume"] = vol
                        return f"Volume set to {vol}"
                    return f"Invalid volume. Must be 1-10"

            # Power
            if "power" in cmd_lower:
                for level in ["low", "medium", "high"]:
                    if level in cmd_lower:
                        self._state["power_level"] = level
                        return f"Power level set to {level}"

            # Waveform
            if "waveform" in cmd_lower or "wideband" in cmd_lower or "narrowband" in cmd_lower:
                if "wideband" in cmd_lower or "wb" in cmd_lower.split():
                    self._state["waveform"] = "WB"
                    return "Waveform set to WB"
                elif "narrowband" in cmd_lower or "nb" in cmd_lower.split():
                    self._state["waveform"] = "NB"
                    return "Waveform set to NB"

        # Toggle commands
        if "enable" in cmd_lower or "turn on" in cmd_lower or "activate" in cmd_lower:
            if "gps" in cmd_lower:
                self._state["gps_on"] = True
                return "GPS enabled"
            elif "led" in cmd_lower:
                self._state["led_on"] = True
                return "LED enabled"
            elif "receive only" in cmd_lower or "rx only" in cmd_lower:
                self._state["rx_only"] = True
                return "Receive only mode enabled"

        if "disable" in cmd_lower or "turn off" in cmd_lower or "deactivate" in cmd_lower:
            if "gps" in cmd_lower:
                self._state["gps_on"] = False
                return "GPS disabled"
            elif "led" in cmd_lower:
                self._state["led_on"] = False
                return "LED disabled"
            elif "receive only" in cmd_lower or "rx only" in cmd_lower:
                self._state["rx_only"] = False
                return "Receive only mode disabled"

        # BIT
        if "perform" in cmd_lower and ("bit" in cmd_lower or "test" in cmd_lower):
            return "BIT completed: All systems nominal"

        return "Not understood"


class RadioClient:
    """
    Client for communicating with the ZCU102 radio target.

    Supports both real TCP connection and simulation mode.
    """

    def __init__(
        self,
        host: str = "192.168.1.11",
        port: int = 5000,
        timeout: float = 5.0,
        simulation_mode: bool = False,
    ):
        """
        Initialize radio client.

        Args:
            host: Target IP address.
            port: Target TCP port.
            timeout: Socket timeout in seconds.
            simulation_mode: If True, use simulated radio instead of TCP.
        """
        self._host = host
        self._port = port
        self._timeout = timeout
        self._simulation_mode = simulation_mode

        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._receive_thread: Optional[threading.Thread] = None
        self._response_queue: queue.Queue[str] = queue.Queue()
        self._running = False

        self._simulated_radio = SimulatedRadio() if simulation_mode else None

    @property
    def is_simulation(self) -> bool:
        """Return True if running in simulation mode."""
        return self._simulation_mode

    @property
    def is_connected(self) -> bool:
        """Return True if connected to target (or in simulation mode)."""
        return self._simulation_mode or self._connected

    def connect(self) -> bool:
        """
        Connect to the radio target.

        Returns:
            True if connection successful or in simulation mode.
        """
        if self._simulation_mode:
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            self._socket.connect((self._host, self._port))
            self._connected = True

            # Start receive thread
            self._running = True
            self._receive_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True,
            )
            self._receive_thread.start()

            return True
        except (socket.error, TimeoutError) as e:
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from the radio target."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except socket.error:
                pass
            self._socket = None
        self._connected = False

    def _receive_loop(self):
        """Background thread to receive responses."""
        while self._running and self._socket:
            try:
                data = self._socket.recv(1024)
                if not data:
                    self._connected = False
                    break
                message = data.decode("utf-8").strip()
                self._response_queue.put(message)
            except socket.timeout:
                continue
            except socket.error:
                self._connected = False
                break

    def send_command(self, command: str, timeout: float = 5.0) -> RadioResponse:
        """
        Send a command to the radio and wait for response.

        Args:
            command: The command to send.
            timeout: How long to wait for response.

        Returns:
            RadioResponse with the result.
        """
        if self._simulation_mode:
            # Add small delay to simulate network latency
            time.sleep(0.1)
            response = self._simulated_radio.process(command)
            return RadioResponse(
                success=response != "Not understood",
                message=response,
                is_simulated=True,
            )

        if not self._connected:
            return RadioResponse(
                success=False,
                message="Not connected to radio",
            )

        # Clear any pending responses
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except queue.Empty:
                break

        # Send command
        try:
            self._socket.sendall(command.encode("utf-8"))
        except socket.error as e:
            self._connected = False
            return RadioResponse(
                success=False,
                message=f"Send failed: {e}",
            )

        # Wait for response
        try:
            response = self._response_queue.get(timeout=timeout)
            return RadioResponse(
                success=response != "Not understood",
                message=response,
            )
        except queue.Empty:
            return RadioResponse(
                success=False,
                message="No response from radio (timeout)",
            )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
