"""
Server-side chart rendering — used only for embedding real chart images
into exported DOCX/PDF reports. The live app renders charts client-side
with Recharts; this is a separate, independent renderer (matplotlib,
headless/Agg backend) so reports don't depend on capturing anything from
the browser. Styled to loosely match the app's palette.
"""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.services import correlation_service, data_service

NAVY = "#1B2A4A"
TEAL = "#2F6F6B"
AMBER = "#C97D34"
GRID = "#E4E1D8"


def _finish(fig) -> bytes:
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _style_axes(ax):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors="#64748B", labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def render_chart(dataset_id: str, chart_type: str, columns: list[str], owner_id: int, title: str = "") -> bytes:
    """Returns PNG bytes for the requested chart. Raises KeyError if the
    dataset is gone, NotOwnedError if it belongs to someone else, ValueError
    for bad columns/chart_type — callers should catch these and skip
    embedding rather than fail the whole export."""
    df = data_service.get_dataset(dataset_id, owner_id=owner_id)

    if chart_type == "line":
        x_col, y_col = columns[0], columns[1]
        sub = df[[x_col, y_col]].dropna()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(sub[x_col], sub[y_col], color=TEAL, linewidth=2)
        ax.set_xlabel(x_col, fontsize=9)
        ax.set_ylabel(y_col, fontsize=9)
        _style_axes(ax)

    elif chart_type == "scatter":
        x_col, y_col = columns[0], columns[1]
        sub = df[[x_col, y_col]].dropna()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.scatter(sub[x_col], sub[y_col], color=NAVY, alpha=0.65, s=16, edgecolors="none")
        ax.set_xlabel(x_col, fontsize=9)
        ax.set_ylabel(y_col, fontsize=9)
        _style_axes(ax)

    elif chart_type == "bar":
        group_col, val_col = columns[0], columns[1]
        sub = df[[group_col, val_col]].dropna()
        means = sub.groupby(group_col)[val_col].mean().sort_index()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.bar(means.index.astype(str), means.values, color=TEAL)
        ax.set_xlabel(group_col, fontsize=9)
        ax.set_ylabel(f"mean({val_col})", fontsize=9)
        _style_axes(ax)

    elif chart_type == "heatmap":
        if len(columns) < 2:
            raise ValueError("Heatmap needs at least 2 columns")
        matrix = correlation_service.correlation_matrix(df, columns, "pearson")
        fig, ax = plt.subplots(figsize=(5, 4.2))
        im = ax.imshow(matrix, cmap="RdYlGn", vmin=-1, vmax=1)
        ax.set_xticks(range(len(columns)))
        ax.set_xticklabels(columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(columns)))
        ax.set_yticklabels(columns, fontsize=8)
        for i in range(len(columns)):
            for j in range(len(columns)):
                val = matrix[i][j]
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(val) > 0.6 else "black")
        fig.colorbar(im, ax=ax, shrink=0.8)

    else:
        raise ValueError(f"Unsupported chart_type: {chart_type}")

    if title:
        ax.set_title(title, fontsize=10, color=NAVY, pad=10)

    return _finish(fig)
