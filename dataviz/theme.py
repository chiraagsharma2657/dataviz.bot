"""Visual theme: brand palette, page styling, and the Plotly chart template.

The colours come from the DataViz logo - deep violet and a bright lime green -
and the chart palette was checked with the data-viz validator rather than by
eye: all eight slots sit in the dark lightness band, clear the chroma floor,
hold >= 3:1 against the chart surface, and keep every adjacent pair apart for
colour-blind readers (worst adjacent CVD dE 11.9, normal-vision dE 15.9).

Slot order is the safety mechanism, not decoration: green, orange, red and
yellow all collapse into each other under deutan simulation, so they are never
adjacent - each is separated by a violet, aqua, blue or magenta.
"""

import base64
from pathlib import Path

# ---------------------------------------------------------------- brand
VIOLET = "#9C6BFF"
LIME = "#A3E635"
PLUM = "#171423"          # chart surface
PLUM_DEEP = "#0F0C1A"     # page plane
PLUM_RAISED = "#1F1A30"   # cards, inputs
BORDER = "rgba(255,255,255,0.10)"

INK = "#F1EDFA"
INK_SOFT = "#B6ADD0"
INK_MUTED = "#8279A0"

# Validated categorical order - do not reorder without re-running the validator.
SERIES = [
    "#9C6BFF",  # violet
    "#6BA015",  # green
    "#D9558F",  # magenta
    "#D2701F",  # orange
    "#1B9AA8",  # aqua
    "#EF5A5A",  # red
    "#5B8DEF",  # blue
    "#A8891A",  # yellow
]

# Single-hue ramp for magnitude (heatmaps), light -> dark.
SEQUENTIAL = [
    "#EBE0FC", "#D5C0F7", "#BFA1F1", "#A882E9",
    "#9063DD", "#7749C6", "#5D36A1", "#45257C",
]

GRID = "#2C2740"
AXIS = "#3A3352"


LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"


def logo_data_uri():
    """Inline the logo so it needs no static file server."""
    if not LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"


def plotly_template():
    """A Plotly template that matches the page, built once and reused."""
    return {
        "layout": {
            "colorway": SERIES,
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {
                "family": 'system-ui, -apple-system, "Segoe UI", sans-serif',
                "color": INK_SOFT,
                "size": 13,
            },
            "title": {"font": {"color": INK, "size": 18}, "x": 0.01, "xanchor": "left"},
            "colorscale": {"sequential": [[i / 7, c] for i, c in enumerate(SEQUENTIAL)]},
            "xaxis": {
                "gridcolor": GRID, "zerolinecolor": AXIS, "linecolor": AXIS,
                "tickfont": {"color": INK_MUTED}, "title": {"font": {"color": INK_SOFT}},
            },
            "yaxis": {
                "gridcolor": GRID, "zerolinecolor": AXIS, "linecolor": AXIS,
                "tickfont": {"color": INK_MUTED}, "title": {"font": {"color": INK_SOFT}},
            },
            "legend": {
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"color": INK_SOFT},
                "orientation": "h", "yanchor": "bottom", "y": 1.02,
                "xanchor": "left", "x": 0,
            },
            "hoverlabel": {
                "bgcolor": PLUM_RAISED,
                "bordercolor": VIOLET,
                "font": {"color": INK, "family": 'system-ui, sans-serif', "size": 13},
            },
            "margin": {"l": 56, "r": 24, "t": 64, "b": 56},
        }
    }


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap');

:root {{
  --violet: {VIOLET};
  --lime: {LIME};
  --plum: {PLUM};
  --plum-raised: {PLUM_RAISED};
  --ink: {INK};
  --ink-soft: {INK_SOFT};
  --border: {BORDER};
}}

/* ---- page plane: deep plum with two soft brand glows ---- */
.stApp {{
  background:
    radial-gradient(1100px 600px at 12% -10%, rgba(156,107,255,0.20), transparent 60%),
    radial-gradient(900px 520px at 92% 8%, rgba(163,230,53,0.10), transparent 60%),
    {PLUM_DEEP};
  color: var(--ink);
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.2rem; max-width: 1180px; }}

/* ---- type ---- */
h1, h2, h3, h4 {{
  font-family: 'Fredoka', system-ui, sans-serif !important;
  color: var(--ink) !important;
  letter-spacing: 0.2px;
}}
h2 {{ font-size: 1.35rem !important; margin-bottom: 0.4rem !important; }}
/* Scoped to the app body, and never to buttons - a blanket span/div rule
   repainted the button label in lavender on lime, which was unreadable. */
.block-container p,
.block-container label,
.block-container > div > div span:not([class*="st-"]) {{
  color: var(--ink-soft);
}}

/* ---- masthead ---- */
.dv-hero {{ text-align: center; padding: 0.5rem 0 0.25rem; }}
.dv-hero img {{
  width: min(420px, 68%);
  filter: drop-shadow(0 10px 30px rgba(156,107,255,0.45));
}}
.dv-tagline {{
  font-family: 'Fredoka', system-ui, sans-serif;
  font-size: 1.02rem;
  color: var(--ink-soft);
  margin: 0.1rem 0 0.3rem;
}}
.dv-rule {{
  height: 2px; border: 0; margin: 1.1rem 0 1.6rem;
  background: linear-gradient(90deg, transparent, var(--violet), var(--lime), transparent);
  opacity: 0.55;
}}

/* ---- section headings with a lime tick ---- */
.dv-step {{
  font-family: 'Fredoka', system-ui, sans-serif;
  font-size: 1.22rem; font-weight: 600; color: var(--ink);
  display: flex; align-items: center; gap: 0.55rem;
  margin: 1.6rem 0 0.7rem;
}}
.dv-step::before {{
  content: ""; width: 4px; height: 20px; border-radius: 3px;
  background: linear-gradient(180deg, var(--violet), var(--lime));
}}

/* ---- cards ---- */
[data-testid="stFileUploader"],
[data-testid="stDataFrame"],
.stPlotlyChart {{
  background: var(--plum-raised);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 0.75rem;
}}
[data-testid="stFileUploader"] {{ padding: 1.1rem; }}
[data-testid="stFileUploader"] section {{
  background: transparent; border: 1.5px dashed rgba(156,107,255,0.5); border-radius: 12px;
}}
[data-testid="stFileUploader"] section:hover {{ border-color: var(--lime); }}

/* ---- inputs ---- */
.stTextInput input {{
  background: var(--plum-raised) !important;
  color: var(--ink) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 0.65rem 0.9rem !important;
}}
.stTextInput input:focus {{
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 3px rgba(156,107,255,0.25) !important;
}}
.stTextInput input::placeholder {{ color: {INK_MUTED} !important; }}

/* ---- buttons: lime, the logo's action colour ---- */
.stButton > button {{
  background: linear-gradient(135deg, var(--lime), #8FCE1E);
  font-family: 'Fredoka', system-ui, sans-serif;
  font-weight: 600;
  border: 0; border-radius: 12px;
  padding: 0.55rem 1.5rem;
  box-shadow: 0 6px 18px rgba(163,230,53,0.28);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}}
/* The label is its own element inside the button, so colour it explicitly -
   contrast 11.4:1 against the lime fill. */
.stButton > button,
.stButton > button *,
.stButton > button:hover *,
.stButton > button:focus * {{
  color: #10180B !important;
  fill: #10180B !important;
}}
.stButton > button:hover {{
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(163,230,53,0.38);
}}

/* ---- SQL code block ---- */
.stCode, pre {{
  background: #120F1D !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}}
code {{ font-size: 0.86rem !important; }}

/* ---- alerts: keep the semantic colour as an edge, not a wash ---- */
[data-testid="stNotification"],
[data-testid="stAlert"],
[data-testid="stAlertContainer"],
.stAlert, .stAlert > div {{
  background: var(--plum-raised) !important;
  border-radius: 14px !important;
  color: var(--ink-soft) !important;
}}
[data-testid="stAlert"], [data-testid="stAlertContainer"], .stAlert {{
  border: 1px solid var(--border) !important;
  border-left: 4px solid var(--violet) !important;
}}
[data-testid="stAlert"] p, [data-testid="stAlertContainer"] p, .stAlert p {{
  color: var(--ink-soft) !important;
}}
/* warning and error keep their own edge colour */
[data-testid="stAlert"]:has(svg[title="warning"]),
.stAlert:has([data-testid="stAlertContentWarning"]) {{
  border-left-color: #E3B341 !important;
}}
[data-testid="stAlert"]:has(svg[title="error"]),
.stAlert:has([data-testid="stAlertContentError"]) {{
  border-left-color: #EF5A5A !important;
}}

/* ---- checkbox accent ---- */
[data-testid="stCheckbox"] svg {{ color: var(--lime); }}

/* ---- stat strip under the preview ---- */
.dv-stats {{ display: flex; gap: 0.8rem; flex-wrap: wrap; margin: 0.7rem 0 0.2rem; }}
.dv-stat {{
  background: var(--plum-raised);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.6rem 1.1rem;
  min-width: 108px;
}}
.dv-stat b {{
  display: block;
  font-family: 'Fredoka', system-ui, sans-serif;
  font-size: 1.5rem; color: var(--ink); line-height: 1.15;
}}
.dv-stat span {{ font-size: 0.78rem; color: {INK_MUTED}; text-transform: uppercase; letter-spacing: 0.6px; }}

/* ---- footer ---- */
.dv-foot {{ text-align: center; color: {INK_MUTED}; font-size: 0.82rem; margin: 2.5rem 0 1rem; }}

#MainMenu, footer {{ visibility: hidden; }}
</style>
"""
