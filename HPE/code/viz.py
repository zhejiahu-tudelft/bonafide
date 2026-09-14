"""Shared chart style for every figure in the report and the deck.

Palette: derived from the Bona Fide template (green #135927 / gold #FCC80D), stepped into the
lightness band so marks stay legible, then validated with the dataviz palette validator on a
white surface (lightness band, chroma floor, CVD separation, normal-vision floor, contrast:
all PASS for the 4-slot set; the 5th slot adds violet for a fifth fixed entity).

Colour follows the entity everywhere: HPE is always green, the S&P 500 always blue, etc.
Comparison series that are not the story are drawn in a recessive context grey.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402

from common import CHARTS  # noqa: E402

# categorical slots (fixed order)
GREEN, GOLD, BLUE, ORANGE, VIOLET = "#2d7d46", "#b8860b", "#2a78d6", "#d9602b", "#7b5cc4"
SERIES = [GREEN, GOLD, BLUE, ORANGE, VIOLET]
ENTITY = {"HPE": GREEN, "SPY": BLUE, "XLK": GOLD, "DELL": ORANGE, "CSCO": VIOLET}
BRAND_GREEN, BRAND_GOLD = "#135927", "#FCC80D"   # template identity colours (titles, headers)
CONTEXT = "#bdbcb5"                               # de-emphasised comparison series
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#ffffff"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"             # status only (never a series)

plt.rcParams.update({
    "font.family": ["DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.axisbelow": True,  # gridlines sit behind bars and other marks
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.frameon": False, "legend.fontsize": 8, "lines.linewidth": 2, "lines.solid_capstyle": "round",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "svg.fonttype": "path",  # text as outlines so SVGs render identically in any browser
})


def figure(w: float = 8.0, h: float = 4.0, nrows: int = 1, height_ratios=None, sharex: bool = True):
    fig, axes = plt.subplots(nrows, 1, figsize=(w, h), sharex=sharex,
                             gridspec_kw={"height_ratios": height_ratios} if height_ratios else None)
    return fig, axes


def titles(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, color=INK, pad=20 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=8.5, va="bottom", gid="subtitle")


def source(fig, text: str) -> None:
    fig.text(0.01, -0.01, f"Source: {text}", color=MUTED, fontsize=7, ha="left", va="top", gid="source")


def pct_axis(ax, decimals: int = 0) -> None:
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=decimals))


def end_label(ax, x, y, text: str, dx: int = 4) -> None:
    """Direct label at a line end, in ink (never the series colour)."""
    ax.annotate(text, (x, y), xytext=(dx, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHARTS / f"{name}.svg", bbox_inches="tight")
    fig.savefig(CHARTS / f"{name}.png", dpi=220, bbox_inches="tight")
    # deck variant: the slide carries the title, subtitle and source line, so hide them in the image
    for ax in fig.axes:
        ax.set_title("")
        for t in ax.texts:
            if t.get_gid() == "subtitle":
                t.set_visible(False)
    for t in fig.texts:
        if t.get_gid() == "source":
            t.set_visible(False)
    fig.savefig(CHARTS / f"{name}_deck.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
