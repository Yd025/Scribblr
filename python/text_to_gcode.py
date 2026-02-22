"""
Convert text into G-code using Hershey single-stroke fonts.

Hardware mapping for the modified machine with Ender 3 board:
  - X motor = horizontal movement on the board
  - Y motor + Z motor = wired in parallel, vertical movement on the board
  - Both Y and Z always receive the same value for vertical moves
  - No chalk lift — chalk stays in contact with the board

Generates G1 commands with feedrate, sent line-by-line over serial.
"""

from python import config
from python.hershey_font import FONT

INIT_COMMANDS = [
    "M203 Y50 Z50",   # unlock max feedrate for Y and Z (50 mm/s = 3000 mm/min)
    "M92 Y400",        # match Y steps/mm to Z steps/mm
    "M211 S0",         # disable soft endstops
    "G91",             # relative positioning
    "M17",             # energize motors
]


class TextToGCode:
    def __init__(self):
        self.cursor_x = 0.0
        self.cursor_y = config.BOARD_HEIGHT - config.CHAR_HEIGHT
        self._initialized = False
        self._machine_x = 0.0
        self._machine_y = 0.0

    def reset_cursor(self):
        self.cursor_x = 0.0
        self.cursor_y = config.BOARD_HEIGHT - config.CHAR_HEIGHT
        self._initialized = False
        self._machine_x = 0.0
        self._machine_y = 0.0

    def get_cursor_position(self) -> tuple[float, float]:
        return self.cursor_x, self.cursor_y

    def convert(self, text: str) -> list[str]:
        """Convert a (possibly multi-line) string to a list of G-code commands."""
        commands = []
        if not self._initialized:
            commands.extend(INIT_COMMANDS)
            self._initialized = True

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            cmds = self._render_line(line)
            commands.extend(cmds)

        return commands

    def _move_to(self, target_x: float, target_y: float, feedrate: int,
                  rapid: bool = False) -> list[str]:
        """Generate a relative move from current machine position to target.
        Y and Z always move together with the same value.
        rapid=True uses G0 (pen up / reposition), rapid=False uses G1 (pen down / draw).
        """
        dx = target_x - self._machine_x
        dy = target_y - self._machine_y

        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return []

        self._machine_x = target_x
        self._machine_y = target_y

        cmd = "G0" if rapid else "G1"
        parts = [cmd]
        if abs(dx) >= 0.01:
            parts.append(f"X{dx:.2f}")
        if abs(dy) >= 0.01:
            parts.append(f"Y{dy:.2f}")
            parts.append(f"Z{dy:.2f}")
        parts.append(f"F{feedrate}")

        return [" ".join(parts)]

    def _render_line(self, text: str) -> list[str]:
        commands = []
        for ch in text:
            glyph = FONT.get(ch.upper() if ch.upper() in FONT else ch, None)
            if glyph is None:
                glyph = FONT.get("?", FONT[" "])

            if self._would_overflow_x(glyph["width"]):
                self._newline()

            if self.cursor_y < 0:
                break

            cmds = self._render_char(glyph)
            commands.extend(cmds)
            self.cursor_x += self._char_advance(glyph["width"])

        self._newline()
        return commands

    def _would_overflow_x(self, glyph_width: int) -> bool:
        advance = self._char_advance(glyph_width)
        return self.cursor_x + advance > config.BOARD_WIDTH

    def _char_advance(self, glyph_width: int) -> float:
        max_font_width = 24
        return (glyph_width / max_font_width) * config.CHAR_WIDTH + config.CHAR_SPACING

    def _newline(self):
        self.cursor_x = 0.0
        self.cursor_y -= (config.CHAR_HEIGHT + config.LINE_SPACING)

    def _render_char(self, glyph: dict) -> list[str]:
        """Render one character at the current cursor position."""
        commands = []
        if not glyph["strokes"]:
            return commands

        max_font_w = 24
        max_font_h = 28

        sx = config.CHAR_WIDTH / max_font_w
        sy = config.CHAR_HEIGHT / max_font_h

        for stroke in glyph["strokes"]:
            if len(stroke) < 2:
                continue

            first = stroke[0]
            px = self.cursor_x + first[0] * sx
            py = self.cursor_y + first[1] * sy

            # Rapid move to stroke start (pen up)
            cmds = self._move_to(px, py, config.RAPID_FEEDRATE, rapid=True)
            commands.extend(cmds)

            # Draw the stroke
            for point in stroke[1:]:
                px = self.cursor_x + point[0] * sx
                py = self.cursor_y + point[1] * sy
                cmds = self._move_to(px, py, config.WRITE_FEEDRATE)
                commands.extend(cmds)

        return commands
