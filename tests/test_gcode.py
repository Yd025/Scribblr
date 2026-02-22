"""
Test G-code generation and visualization.
Feeds hardcoded text to the G-code generator and renders a preview.

Usage:
    python -m tests.test_gcode
    python -m tests.test_gcode --text "Hello World"
    python -m tests.test_gcode --text "Lin Algebra" --save preview.png
"""

import argparse

from python.text_to_gcode import TextToGCode
from tests.gcode_visualizer import visualize


def main():
    parser = argparse.ArgumentParser(description="Test G-code generation")
    parser.add_argument("--text", type=str, default=None, help="Text to render")
    parser.add_argument("--save", type=str, default=None, help="Save plot to file")
    args = parser.parse_args()

    text = args.text or "HELLO\nWORLD"

    print(f"Rendering: {repr(text)}\n")

    gcode_gen = TextToGCode()
    commands = gcode_gen.convert(text)

    print(f"Generated {len(commands)} G-code commands")
    print()
    print("── First 20 commands ───────────────────────────────")
    for cmd in commands[:20]:
        print(f"  {cmd}")
    if len(commands) > 20:
        print(f"  ... ({len(commands) - 20} more)")
    print()

    visualize(commands, title=f"Preview: {text!r}", save_path=args.save, show=not args.save)


if __name__ == "__main__":
    main()
