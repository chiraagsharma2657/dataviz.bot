"""Turning a chart spec from the model into a Plotly figure."""

import plotly.express as px

CHART_TYPES = ["bar", "line", "scatter", "hist", "box", "heatmap", "pie"]


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

    if kind == "bar":
        fig = px.bar(result, x=x, y=y, color=hue, title=title, barmode="group")
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
            color_continuous_scale="Viridis",
            labels={"x": x, "y": y, "color": hue},
        )
    elif kind == "pie":
        fig = px.pie(result, names=x, values=y, title=title, hole=0.0)
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
        )

    # Show the exact underlying value on hover for every point.
    if kind in ("bar", "line", "scatter"):
        fig.update_traces(
            hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y}}<extra></extra>"
        )
    elif kind == "hist":
        fig.update_traces(hovertemplate=f"{x}: %{{x}}<br>count: %{{y}}<extra></extra>")

    fig.update_layout(
        hovermode="closest",
        margin=dict(l=40, r=20, t=60, b=40),
        legend_title_text=hue or "",
        xaxis_title=x,
    )
    if kind not in ("pie", "heatmap"):
        fig.update_xaxes(tickangle=-45)
        fig.update_layout(yaxis_title=y or "count")
    return fig
