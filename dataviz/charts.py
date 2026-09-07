"""Turning a chart spec from the model into a Plotly figure."""

import plotly.express as px
import plotly.io as pio

from . import theme

CHART_TYPES = ["bar", "line", "scatter", "hist", "box", "heatmap", "pie"]

# Register the brand template once and make it the default for every figure.
pio.templates["dataviz"] = theme.plotly_template()
pio.templates.default = "plotly_white+dataviz"


MAX_SERIES = len(theme.SERIES)


def _fold_to_other(result, hue, y):
    """Keep the biggest categories and fold the tail into one "Other" series.

    Plotly cycles its colourway when there are more categories than colours, so
    a 9th series silently repeats the 1st and two unrelated categories end up
    the same colour. The palette is only colour-blind-safe as a fixed set, so
    the fix is fewer series, never more colours.
    """
    if not hue or result[hue].nunique() <= MAX_SERIES:
        return result, False

    ranked = (result.groupby(hue)[y].sum().sort_values(ascending=False)
              if y else result[hue].value_counts())
    keep = set(ranked.index[:MAX_SERIES - 1])

    folded = result.copy()
    folded[hue] = folded[hue].where(folded[hue].isin(keep), "Other")
    return folded, True


def _is_row_label(result, x, hue):
    """True when `hue` labels individual rows rather than grouping them.

    "The top product per country" returns one row per country, each with its
    own product name. Colouring by product then splits the axis into as many
    grouped slots as there are products, so every bar is a sliver a pixel wide
    and the chart reads as empty. The label belongs in the tooltip instead.
    """
    return bool(hue) and x and len(result) == result[x].nunique()


def draw_chart(result, chart):
    """Render one interactive Plotly chart from the spec the model returned."""
    kind = (chart.get("type") or "").lower()
    if kind not in CHART_TYPES:
        raise ValueError(f"Unsupported chart type: {kind or 'none'}")

    x = chart.get("x")
    y = chart.get("y")
    hue = chart.get("hue")
    title = chart.get("title") or ""

    for col in (x, y, hue):
        if col and col not in result.columns:
            raise ValueError(f"Column '{col}' is not in the result table.")

    # A per-row label is moved out of the colour channel and into the tooltip.
    row_label = None
    if kind in ("bar", "line") and _is_row_label(result, x, hue):
        row_label, hue = hue, None

    folded = False
    if kind in ("bar", "line", "scatter", "box", "hist"):
        result, folded = _fold_to_other(result, hue, y)

    # Longest bars first - a ranking is unreadable in arbitrary order.
    if kind == "bar" and y and not hue and result[x].nunique() == len(result):
        result = result.sort_values(y, ascending=False)

    if kind == "bar":
        custom = [row_label] if row_label else None
        fig = px.bar(result, x=x, y=y, color=hue, title=title, barmode="group",
                     custom_data=custom)
    elif kind == "line":
        fig = px.line(result, x=x, y=y, color=hue, title=title, markers=True)
    elif kind == "scatter":
        fig = px.scatter(result, x=x, y=y, color=hue, title=title)
    elif kind == "hist":
        fig = px.histogram(result, x=x, color=hue, title=title)
    elif kind == "box":
        fig = px.box(result, x=x, y=y, color=hue, title=title, points="all")
    elif kind == "heatmap":
        pivot = result.pivot_table(index=y, columns=x, values=hue, aggfunc="mean")
        fig = px.imshow(
            pivot,
            title=title,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale=theme.SEQUENTIAL,
            labels={"x": x, "y": y, "color": hue},
        )
    elif kind == "pie":
        fig = px.pie(result, names=x, values=y, title=title, hole=0.0)
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
        )

    # Mark specs: rounded data-ends on bars, thin lines, generous hit targets,
    # and a 2px surface-coloured gap so adjacent fills never bleed together.
    if kind == "bar":
        fig.update_traces(marker_line_color=theme.PLUM, marker_line_width=2)
        fig.update_layout(bargap=0.28, bargroupgap=0.08)
    elif kind == "line":
        fig.update_traces(line_width=2, marker_size=8)
    elif kind == "scatter":
        fig.update_traces(marker_size=9,
                          marker_line_color=theme.PLUM, marker_line_width=1.5)
    elif kind == "pie":
        fig.update_traces(marker_line_color=theme.PLUM, marker_line_width=2)

    # Show the exact underlying value on hover for every point. When a per-row
    # label was pulled out of the colour channel, it reappears here.
    if kind in ("bar", "line", "scatter"):
        label_line = f"{row_label}: %{{customdata[0]}}<br>" if row_label else ""
        fig.update_traces(
            hovertemplate=f"<b>%{{x}}</b><br>{label_line}{y}: %{{y}}<extra></extra>"
        )
    elif kind == "hist":
        fig.update_traces(hovertemplate=f"{x}: %{{x}}<br>count: %{{y}}<extra></extra>")

    fig.update_layout(
        hovermode="closest",
        legend_title_text=hue or "",
        xaxis_title=x,
    )

    # A wrapping legend used to sit on top of the title. Past a few entries it
    # moves below the plot, where it has room to wrap.
    series_count = len(fig.data)
    if series_count < 2:
        fig.update_layout(showlegend=False)
    elif series_count > 4:
        fig.update_layout(legend=dict(
            orientation="h", yanchor="top", y=-0.32,
            xanchor="left", x=0, title_text="",
        ))

    # Rotated country names need room; a legend underneath needs more.
    bottom = 150 if series_count > 4 else 110
    fig.update_layout(margin=dict(l=64, r=28, t=72, b=bottom))

    if kind not in ("pie", "heatmap"):
        fig.update_xaxes(tickangle=-45, automargin=True)
        fig.update_layout(yaxis_title=y or "count")

    if folded:
        fig.add_annotation(
            text=f"Smaller {hue} values grouped as “Other”",
            xref="paper", yref="paper", x=0, y=1.06, showarrow=False,
            font=dict(size=11, color=theme.INK_MUTED), xanchor="left",
        )
    return fig
