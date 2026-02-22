"""
Diagnostic motor test — reads back every response from the board.
Usage:
    python3 tests/test_simple.py
    python3 tests/test_simple.py --port /dev/cu.usbmodemSN234567892
"""

import serial
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="/dev/cu.usbmodemSN234567892")
parser.add_argument("--baud", type=int, default=115200)
args = parser.parse_args()


def read_all(ser, wait=1.0):
    """Read everything the board sends for `wait` seconds."""
    end = time.time() + wait
    lines = []
    while time.time() < end:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                lines.append(line)
                print(f"  << {line}")
        else:
            time.sleep(0.05)
    return lines


def send(ser, cmd):
    """Send a command and print what the board replies."""
    print(f"  >> {cmd}")
    ser.write((cmd + "\n").encode("utf-8"))
    read_all(ser, wait=1.5)


print(f"=== Opening {args.port} at {args.baud} baud ===")
printer = serial.Serial(args.port, args.baud, timeout=1)

print("\n=== Waiting for boot (10s) — watch for messages ===")
boot = read_all(printer, wait=10)
if not boot:
    print("  (no boot messages — board may not have reset or wrong port)")

print("\n=== Sending M115 (report firmware) ===")
send(printer, "M115")

print("\n=== Sending init commands ===")
send(printer, "M203 Y50 Z50")
send(printer, "M92 Y400")
send(printer, "M211 S0")
send(printer, "G91")
send(printer, "M17")

print("\n=== Moving X +10mm ===")
send(printer, "G1 X10 F3000")
time.sleep(2)

print("\n=== Moving X -10mm ===")
send(printer, "G1 X-10 F3000")
time.sleep(2)

print("\n=== Moving Y+Z +10mm ===")
send(printer, "G1 Y10 Z10 F300")
time.sleep(2)

print("\n=== Moving Y+Z -10mm ===")
send(printer, "G1 Y-10 Z-10 F300")
time.sleep(2)

print("\n=== M84 (disable motors) ===")
send(printer, "M84")

printer.close()
print("\n=== Done ===")
