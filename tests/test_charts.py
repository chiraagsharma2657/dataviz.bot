"""Chart construction: series limits, per-row labels, and readable bars."""

import pandas as pd
import pytest

from dataviz import theme
from dataviz.charts import MAX_SERIES, draw_chart


def test_palette_is_never_cycled():
    """More categories than colours must fold, not repeat a hue.

    Plotly cycles its colourway by default, which hands two unrelated
    categories the same colour and quietly breaks the colour-blind-safe set.
    """
    df = pd.DataFrame({
        "region": ["A", "B"] * 20,
        "product": [f"P{i}" for i in range(20)] * 2,
        "qty": list(range(40)),
    })
    fig = draw_chart(df, {"type": "bar", "x": "region", "y": "qty",
                          "hue": "product", "title": "t"})
    colors = [t.marker.color for t in fig.data]
    assert len(fig.data) <= MAX_SERIES
    assert len(colors) == len(set(colors))
    assert "Other" in [t.name for t in fig.data]


def test_biggest_categories_survive_the_fold():
    df = pd.DataFrame({
        "x": ["A"] * 10,
        "cat": [f"c{i}" for i in range(10)],
        "v": [100, 90, 80, 70, 60, 50, 5, 4, 3, 2],
    })
    fig = draw_chart(df, {"type": "bar", "x": "x", "y": "v",
                          "hue": "cat", "title": "t"})
    names = [t.name for t in fig.data]
    assert "c0" in names and "c1" in names   # largest kept
    assert "c9" not in names                 # smallest folded away
    assert "Other" in names


def test_per_row_label_does_not_split_the_axis():
    """One row per x with a unique label each: colouring by it would slice
    every bar into a sliver, so the label belongs in the tooltip."""
    df = pd.DataFrame({
        "country": ["IN", "US", "FR"],
        "product": ["A", "B", "C"],
        "qty": [10, 30, 20],
    })
    fig = draw_chart(df, {"type": "bar", "x": "country", "y": "qty",
                          "hue": "product", "title": "t"})
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 3
    assert "product" in fig.data[0].hovertemplate


def test_single_series_bars_are_sorted_descending():
    df = pd.DataFrame({"city": ["A", "B", "C"], "total": [5, 30, 12]})
    fig = draw_chart(df, {"type": "bar", "x": "city", "y": "total",
                          "hue": None, "title": "t"})
    assert list(fig.data[0].y) == [30, 12, 5]


def test_one_series_has_no_legend():
    df = pd.DataFrame({"city": ["A", "B"], "total": [5, 30]})
    fig = draw_chart(df, {"type": "bar", "x": "city", "y": "total",
                          "hue": None, "title": "t"})
    assert fig.layout.showlegend is False


def test_many_series_move_the_legend_below_the_plot():
    df = pd.DataFrame({
        "x": ["A", "B"] * 6,
        "cat": [f"c{i}" for i in range(6)] * 2,
        "v": range(12),
    })
    fig = draw_chart(df, {"type": "bar", "x": "x", "y": "v",
                          "hue": "cat", "title": "t"})
    assert fig.layout.legend.y < 0      # below, not overlapping the title


@pytest.mark.parametrize("kind,spec", [
    ("bar", {"x": "city", "y": "total", "hue": None}),
    ("line", {"x": "city", "y": "total", "hue": None}),
    ("scatter", {"x": "total", "y": "profit", "hue": None}),
    ("hist", {"x": "total", "y": None, "hue": None}),
    ("box", {"x": "city", "y": "total", "hue": None}),
    ("pie", {"x": "city", "y": "total", "hue": None}),
])
def test_every_chart_type_still_renders(kind, spec):
    df = pd.DataFrame({
        "city": ["A", "B", "C", "D"],
        "total": [10, 30, 20, 15],
        "profit": [1.5, 3.0, 2.2, 1.8],
    })
    fig = draw_chart(df, {"type": kind, "title": "t", **spec})
    assert fig.data


def test_unknown_column_is_rejected():
    df = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(ValueError, match="not in the result table"):
        draw_chart(df, {"type": "bar", "x": "nope", "y": "a", "hue": None,
                        "title": "t"})


def test_series_palette_matches_the_validated_order():
    """A reorder here would invalidate the colour-blindness checks recorded in
    theme.py, so the first slots are pinned."""
    assert theme.SERIES[:3] == ["#9C6BFF", "#6BA015", "#D9558F"]
    assert len(theme.SERIES) == 8
