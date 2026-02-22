"""
Machine communication — sends G-code to the printer board via
USB Serial or WiFi TCP socket.

Serial mode: fire-and-forget writes matching the working jog controller.
Marlin buffers commands internally, so we just write and add a small delay.
"""

import socket
import time
import serial
from python import config

CMD_DELAY = 0.05  # seconds between commands (50ms)


class MachineConnection:
    """Abstract base for serial / wifi connections."""

    def send(self, gcode_line: str):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class SerialConnection(MachineConnection):
    def __init__(self, port: str = None, baud: int = None):
        self.port = port or config.SERIAL_PORT
        if not self.port:
            raise RuntimeError(
                "No serial port specified. Use --port /dev/cu.usbmodemXXXX "
                "or set SERIAL_PORT in config.py. Run `ls /dev/cu.usb*` to find yours."
            )
        self.baud = baud or config.SERIAL_BAUD
        print(f"[SERIAL] Opening {self.port} @ {self.baud} baud ...")
        self._ser = serial.Serial(self.port, self.baud, timeout=2)
        print("[SERIAL] Waiting for board to boot (this takes ~8s) ...")
        self._wait_for_boot()
        print("[SERIAL] Ready.")

    def _wait_for_boot(self):
        """Wait for Marlin to finish booting by reading until we see 'start' or a timeout."""
        deadline = time.time() + 10
        saw_anything = False
        while time.time() < deadline:
            if self._ser.in_waiting:
                line = self._ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"[SERIAL] << {line}")
                    saw_anything = True
                    if "start" in line.lower():
                        time.sleep(0.5)
                        break
            else:
                time.sleep(0.25)
        if not saw_anything:
            print("[SERIAL] (no boot messages received — board may not have reset)")

    def send(self, gcode_line: str):
        """Fire-and-forget: write the command, don't wait for ok."""
        line = gcode_line.strip() + "\n"
        self._ser.write(line.encode("utf-8"))
        time.sleep(CMD_DELAY)

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()


class WifiConnection(MachineConnection):
    def __init__(self, host: str = None, port: int = None):
        self.host = host or config.WIFI_HOST
        self.port = port or config.WIFI_PORT
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(10)
        self._sock.connect((self.host, self.port))
        self._file = self._sock.makefile("r")
        time.sleep(1)

    def send(self, gcode_line: str):
        line = gcode_line.strip() + "\n"
        self._sock.sendall(line.encode("ascii"))
        while True:
            resp = self._file.readline().strip()
            if resp.lower().startswith("ok"):
                return
            if "error" in resp.lower():
                print(f"[WIFI] Error response: {resp}")
                return

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass


class DummyConnection(MachineConnection):
    """Prints G-code to stdout instead of sending to hardware.
    Useful for testing without a machine connected.
    """

    def send(self, gcode_line: str):
        print(f"[GCODE] {gcode_line.strip()}")

    def close(self):
        pass


def connect(mode: str = None, port: str = None) -> MachineConnection:
    """Factory: returns the appropriate connection based on config or override."""
    mode = mode or config.COMM_MODE
    if mode == "serial":
        return SerialConnection(port=port)
    elif mode == "wifi":
        return WifiConnection()
    elif mode == "dummy":
        return DummyConnection()
    else:
        raise ValueError(f"Unknown comm mode: {mode}")
