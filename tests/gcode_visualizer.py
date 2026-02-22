"""
G-code visualizer — renders G-code commands as a 2D matplotlib plot
showing exactly what the chalk would draw on the board.

  G0 moves → dashed gray (rapid / chalk up)
  G1 moves → solid blue  (drawing / chalk down)
"""

import re
import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from python import config


def parse_gcode(commands: list[str]) -> list[dict]:
    """Parse G-code commands into a list of move dicts.
    Supports both G90 (absolute) and G91 (relative) positioning.
    """
    moves = []
    current = {"x": 0.0, "y": 0.0, "z": 0.0}
    relative = False

    for line in commands:
        line = line.strip()
        if not line or line.startswith(";"):
            continue

        parts = line.split()
        cmd = parts[0].upper()

        if cmd == "G90":
            relative = False
            continue
        if cmd == "G91":
            relative = True
            continue

        params = {}
        for p in parts[1:]:
            m = re.match(r"([A-Z])(-?[\d.]+)", p, re.IGNORECASE)
            if m:
                params[m.group(1).upper()] = float(m.group(2))

        if cmd in ("G0", "G1"):
            new = dict(current)
            new["cmd"] = cmd
            if relative:
                if "X" in params:
                    new["x"] += params["X"]
                if "Y" in params:
                    new["y"] += params["Y"]
                if "Z" in params:
                    new["z"] += params["Z"]
            else:
                if "X" in params:
                    new["x"] = params["X"]
                if "Y" in params:
                    new["y"] = params["Y"]
                if "Z" in params:
                    new["z"] = params["Z"]
            moves.append({"from": dict(current), "to": new, "cmd": cmd})
            current = {k: new[k] for k in ("x", "y", "z")}

    return moves


def visualize(
    commands: list[str],
    title: str = "G-Code Preview",
    save_path: str | None = None,
    show: bool = True,
):
    """Render G-code as a matplotlib plot.

    Args:
        commands: list of G-code strings
        title: plot title
        save_path: if set, save the figure to this file
        show: if True, display the plot interactively
    """
    if not show:
        matplotlib.use("Agg")

    moves = parse_gcode(commands)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_xlim(-10, config.BOARD_WIDTH + 10)
    ax.set_ylim(-10, config.BOARD_HEIGHT + 10)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")

    board = patches.Rectangle(
        (0, 0),
        config.BOARD_WIDTH,
        config.BOARD_HEIGHT,
        linewidth=2,
        edgecolor="black",
        facecolor="#2d2d2d",
    )
    ax.add_patch(board)

    for move in moves:
        x0, y0 = move["from"]["x"], move["from"]["y"]
        x1, y1 = move["to"]["x"], move["to"]["y"]

        if abs(x1 - x0) < 0.001 and abs(y1 - y0) < 0.001:
            continue

        if move["cmd"] == "G1":
            ax.plot(
                [x0, x1],
                [y0, y1],
                color="white",
                linewidth=2.5,
                solid_capstyle="round",
            )
        else:
            ax.plot(
                [x0, x1],
                [y0, y1],
                color="gray",
                linewidth=0.3,
                linestyle="--",
                alpha=0.3,
            )

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved preview to {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig
