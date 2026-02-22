"""
Test machine communication — initialize the board and send movement commands.
Matches the initialization sequence from the working jog controller.

Usage:
    python -m tests.test_comm --mode serial
    python -m tests.test_comm --mode serial --port /dev/cu.usbserial-14330
    python -m tests.test_comm --mode dummy
"""

import argparse
import time

from python import machine_comm


def main():
    parser = argparse.ArgumentParser(description="Test machine communication")
    parser.add_argument(
        "--mode",
        choices=["serial", "wifi", "dummy"],
        default="dummy",
        help="Communication mode",
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port (e.g. /dev/cu.usbserial-14330)",
    )
    args = parser.parse_args()

    print(f"Connecting in '{args.mode}' mode ...")
    conn = machine_comm.connect(args.mode, port=args.port)
    print()

    # ── Initialize (same sequence as working jog controller) ──
    print("── Initializing board ──")
    init_commands = [
        ("M203 Y50 Z50",  "Unlock Y/Z max speed"),
        ("M92 Y400",       "Match Y steps to Z steps"),
        ("M211 S0",        "Disable soft endstops"),
        ("G91",            "Relative positioning"),
        ("M17",            "Energize motors"),
    ]
    for cmd, desc in init_commands:
        print(f"  >>> {cmd:20s}  ({desc})")
        conn.send(cmd)
        time.sleep(0.2)

    print("\n  Waiting 3s for init to settle ...\n")
    time.sleep(3)

    # ── Test movements ──
    print("── Testing movements (watch the machine!) ──")
    test_moves = [
        ("G1 X10 F3000",          "X +10mm"),
        ("G1 X-10 F3000",         "X -10mm"),
        ("G1 Y10 Z10 F300",       "Y+Z +10mm (vertical up)"),
        ("G1 Y-10 Z-10 F300",     "Y+Z -10mm (vertical down)"),
        ("G1 X20 Y5 Z5 F1500",    "Diagonal"),
        ("G1 X-20 Y-5 Z-5 F1500", "Diagonal back"),
    ]

    for cmd, desc in test_moves:
        print(f"  >>> {cmd:30s}  ({desc})")
        conn.send(cmd)
        time.sleep(2)
        print(f"      ✓")

    # ── Disable motors ──
    print("\n── Disabling motors ──")
    conn.send("M84")
    time.sleep(0.5)
    print("  Motors disabled (M84).\n")

    print("All done. Closing connection.")
    conn.close()


if __name__ == "__main__":
    main()
