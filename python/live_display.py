"""
Live chalkboard display — shows drawing in real-time as G-code executes.
Uses tkinter so it can be AirPlayed to an external display.

The window shows a dark board and draws white lines matching
exactly what the machine is writing, stroke by stroke.
"""

import tkinter as tk
import re
import math
from python import config

PADDING = 40
BG_COLOR = "#1a1a1a"
CHALK_COLOR = "#ffffff"
RAPID_COLOR = "#333333"
LINE_WIDTH = 3
RAPID_WIDTH = 1


class LiveDisplay:
    def __init__(self, fullscreen=True, speed=1.0):
        self.root = tk.Tk()
        self.root.title("Chalkboard Live")
        self.root.configure(bg="black")

        if fullscreen:
            self.root.attributes("-fullscreen", True)
            self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
        else:
            sw, sh = 1000, 1000
            self.root.geometry(f"{sw}x{sh}")

        board_aspect = config.BOARD_WIDTH / config.BOARD_HEIGHT
        available_w = sw - 2 * PADDING
        available_h = sh - 2 * PADDING

        if available_w / available_h > board_aspect:
            self.board_px_h = available_h
            self.board_px_w = int(available_h * board_aspect)
        else:
            self.board_px_w = available_w
            self.board_px_h = int(available_w / board_aspect)

        self.offset_x = (sw - self.board_px_w) // 2
        self.offset_y = (sh - self.board_px_h) // 2

        self.scale_x = self.board_px_w / config.BOARD_WIDTH
        self.scale_y = self.board_px_h / config.BOARD_HEIGHT

        self.canvas = tk.Canvas(
            self.root,
            width=sw,
            height=sh,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.canvas.create_rectangle(
            self.offset_x, self.offset_y,
            self.offset_x + self.board_px_w,
            self.offset_y + self.board_px_h,
            fill=BG_COLOR, outline="#444444", width=2,
        )

        self.canvas.create_text(
            sw // 2, sh - 12,
            text="Q = quit  |  ESC = toggle fullscreen",
            fill="#555555", font=("Helvetica", 12),
        )

        self.root.bind("<q>", lambda e: self._quit())
        self.root.bind("<Q>", lambda e: self._quit())
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        self.speed = speed
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.relative = False
        self._command_queue = []
        self._running = False

    def _to_screen(self, board_x, board_y):
        """Convert board mm coordinates to screen pixels (flip Y)."""
        sx = self.offset_x + board_x * self.scale_x
        sy = self.offset_y + self.board_px_h - board_y * self.scale_y
        return sx, sy

    def _calc_duration_ms(self, dx, dy, feedrate):
        """How long this move takes in real time (feedrate is mm/min)."""
        dist = math.sqrt(dx * dx + dy * dy)
        if feedrate <= 0 or dist < 0.01:
            return 10
        speed_mm_per_s = feedrate / 60.0
        seconds = dist / speed_mm_per_s
        return max(10, int(seconds * 1000))

    def execute_commands(self, commands, serial_conn=None, on_done=None):
        """Queue G-code commands for animated execution.
        Optionally also sends each command to serial_conn.
        """
        self._command_queue = list(commands)
        self._serial = serial_conn
        self._on_done = on_done
        self._running = True
        self._process_next()

    def _process_next(self):
        if not self._command_queue:
            self._running = False
            if self._on_done:
                self.root.after(100, self._on_done)
            return

        cmd = self._command_queue.pop(0)
        delay = self._execute_one(cmd)

        if self._serial:
            self._serial.send(cmd)

        self.root.after(delay, self._process_next)

    def _execute_one(self, line):
        """Execute one G-code command on the canvas. Returns delay in ms."""
        line = line.strip()
        if not line:
            return 10

        parts = line.split()
        cmd = parts[0].upper()

        if cmd == "G90":
            self.relative = False
            return 10
        if cmd == "G91":
            self.relative = True
            return 10
        if cmd not in ("G0", "G1"):
            return 50

        params = {}
        for p in parts[1:]:
            m = re.match(r"([A-Z])(-?[\d.]+)", p, re.IGNORECASE)
            if m:
                params[m.group(1).upper()] = float(m.group(2))

        feedrate = params.get("F", config.WRITE_FEEDRATE)
        dx_raw = params.get("X", 0)
        dy_raw = params.get("Y", 0)

        if self.relative:
            new_x = self.pos_x + dx_raw
            new_y = self.pos_y + dy_raw
        else:
            new_x = params.get("X", self.pos_x)
            new_y = params.get("Y", self.pos_y)

        old_sx, old_sy = self._to_screen(self.pos_x, self.pos_y)
        new_sx, new_sy = self._to_screen(new_x, new_y)

        dx = new_x - self.pos_x
        dy = new_y - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0.1:
            is_draw = (cmd == "G1")
            color = CHALK_COLOR if is_draw else RAPID_COLOR
            width = LINE_WIDTH if is_draw else RAPID_WIDTH
            self.canvas.create_line(
                old_sx, old_sy, new_sx, new_sy,
                fill=color, width=width, capstyle=tk.ROUND,
            )

        self.pos_x = new_x
        self.pos_y = new_y

        duration = self._calc_duration_ms(dx, dy, feedrate)
        return max(1, int(duration / self.speed))

    def _quit(self):
        """Clean shutdown."""
        self._command_queue.clear()
        self._running = False
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        """Start the tkinter main loop."""
        self.root.mainloop()

    def close(self):
        self._quit()
