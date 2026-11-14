"""One shared chart style so every figure in the repo looks like a set.

Rules: the title states the finding, one highlight colour carries the point,
everything else is grey, values are labelled on the marks, the grid is faint.
Rule colours are fixed per rule so the same rule looks the same in every chart.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3de"
OTHER = "#c9c8c2"        # de-emphasised marks
HIGHLIGHT = "#2a78d6"    # the one thing the chart is about

RULE_COLORS = {          # fixed per entity, never by rank
    "A": "#eb6834",
    "B": "#2a78d6",
    "C": "#1baf7a",
    "Built-in": "#8a8984",
}
MODEL_COLOR = "#6250d6"

FIGSIZE = (10, 6)
DPI = 200


def apply():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "text.color": TEXT,
        "axes.labelcolor": TEXT_2,
        "axes.labelsize": 11,
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "lines.linewidth": 2,
    })


def new(left=0.10):
    apply()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    fig.subplots_adjust(left=left, right=0.95, top=0.80, bottom=0.14)
    return fig, ax


def finish(fig, title, subtitle, source, path):
    fig.text(0.03, 0.935, title, fontsize=16, fontweight="bold", color=TEXT, ha="left")
    fig.text(0.03, 0.88, subtitle, fontsize=11, color=TEXT_2, ha="left")
    fig.text(0.03, 0.025, source, fontsize=8.5, color=MUTED, ha="left")
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"  saved {path.name}")
