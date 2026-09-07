"""DataViz: upload a CSV, ask a question in plain English, get a table and a chart."""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from dataviz import theme
from dataviz.charts import draw_chart
from dataviz.landing import forget_key_button, require_api_key, resolve_api_key
from dataviz.data import normalize_dates, run_query, to_table_name
from dataviz.llm import (
    ModelError, QuotaExceeded, ask, build_model, parse_chart_reply, strip_fences,
)
from dataviz.prompts import chart_prompt, sql_prompt
from dataviz.sql import is_select, repair_sql

load_dotenv()

st.set_page_config(
    page_title="DataViz",
    page_icon=str(theme.LOGO_PATH) if theme.LOGO_PATH.exists() else "*",
    layout="wide",
)
st.markdown(theme.CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_model(api_key):
    return build_model(api_key=api_key)


def step(label):
    st.markdown(f'<div class="dv-step">{label}</div>', unsafe_allow_html=True)


# Landing page first: without a key there is nothing the app can do.
# REQUIRE_USER_KEY forces it even when the server has a key of its own.
api_key = resolve_api_key() or require_api_key()

# ------------------------------------------------------------- masthead
logo = theme.logo_data_uri()
if logo:
    st.markdown(
        f'<div class="dv-hero"><img src="{logo}" alt="DataViz">'
        '<p class="dv-tagline">Ask your data anything. No SQL required.</p></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="dv-hero"><h1>DataViz</h1>'
                '<p class="dv-tagline">Ask your data anything. No SQL required.</p></div>',
                unsafe_allow_html=True)
st.markdown('<hr class="dv-rule">', unsafe_allow_html=True)

try:
    model = get_model(api_key)
except RuntimeError as e:
    st.error(str(e))
    st.stop()

# ---------------------------------------------------------------- 1. Upload
step("Upload your data")
file = st.file_uploader("Drop a CSV file here", type=["csv"], label_visibility="collapsed")

df = None
date_cols = []
if file is not None:
    df = pd.read_csv(file)
    df, date_cols = normalize_dates(df)

    st.markdown(
        '<div class="dv-stats">'
        f'<div class="dv-stat"><b>{len(df):,}</b><span>Rows</span></div>'
        f'<div class="dv-stat"><b>{len(df.columns)}</b><span>Columns</span></div>'
        f'<div class="dv-stat"><b>{len(date_cols)}</b><span>Date fields</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.expander(f"Preview — {file.name}", expanded=True):
        st.dataframe(df.head(8), use_container_width=True)

    database = st.text_input(
        "Database name",
        value=f"{to_table_name(file.name)}_db",
        key=f"db_{file.name}",
    )

# ------------------------------------------------------------------ 2. Ask
if df is None:
    st.info("Upload a CSV file to start asking questions.")
    st.markdown('<div class="dv-foot">DataViz — powered by Gemini</div>',
                unsafe_allow_html=True)
    st.stop()

step("Ask a question")
question = st.text_input(
    "What do you want to see from this dataset?",
    placeholder="e.g. Top 10 cities by total sales",
    key="question",
    label_visibility="collapsed",
)

# Only call the model when the question actually changed, so that toggling the
# chart options below does not re-run the query on every Streamlit rerun.
if question and st.session_state.get("answered_question") != question:
    table = to_table_name(file.name)

    try:
        with st.spinner("Conjuring your query..."):
            reply = ask(model, sql_prompt(database, table, df, date_cols, question))
    except QuotaExceeded as e:
        st.warning(str(e), icon="⏳")
        st.stop()
    except ModelError as e:
        st.error(str(e))
        st.stop()

    raw_query = strip_fences(reply)
    # The model writes MySQL; this makes it run correctly on SQLite dates.
    query = repair_sql(raw_query)

    st.session_state["answered_question"] = question
    st.session_state["query"] = query
    st.session_state["repaired"] = query != raw_query
    st.session_state["result"] = None
    st.session_state["error"] = None
    st.session_state["chart_spec"] = None

    if is_select(query):
        try:
            st.session_state["result"] = run_query(df, table, query)
        except Exception as e:
            st.session_state["error"] = f"Could not run the query on the uploaded data: {e}"

# --------------------------------------------------------------- 3. Result
query = st.session_state.get("query")
result = st.session_state.get("result")

if query:
    step("The query")
    st.code(query, language="sql")
    if st.session_state.get("repaired"):
        st.caption("Adjusted the generated SQL so its date handling works on this engine.")

    if not is_select(query):
        st.warning(query)
    elif st.session_state.get("error"):
        st.error(st.session_state["error"])

if result is not None:
    step("The answer")
    st.dataframe(result, use_container_width=True)
    st.caption(f"{len(result):,} row(s)")

    # An empty result is easy to mistake for a broken app, so say what it means.
    if result.empty:
        st.warning(
            "The query ran but matched no rows. Check that the values you asked "
            "for exist in the data"
            + (f" - date columns cover {df[date_cols[0]].min()} to "
               f"{df[date_cols[0]].max()}." if date_cols else ".")
        )

    # ------------------------------------------------------- 4. Optional chart
    if not result.empty and st.checkbox("Visualize this result", key="want_chart"):
        step("The picture")
        chart_request = st.text_input(
            "How would you like it drawn? (optional)",
            placeholder="e.g. bar chart of sales by city, or leave blank to let DataViz decide",
            key="chart_request",
        )

        if st.button("Create chart", key="make_chart"):
            try:
                with st.spinner("Designing your chart..."):
                    chart_reply = ask(model, chart_prompt(
                        st.session_state.get("answered_question", ""),
                        result,
                        chart_request,
                    ))
                st.session_state["chart_spec"] = parse_chart_reply(chart_reply)
            except QuotaExceeded as e:
                # The table above is still good, so keep the page and just say
                # the chart could not be planned.
                st.warning(str(e), icon="⏳")
            except ModelError as e:
                st.error(str(e))

        spec = st.session_state.get("chart_spec")
        if spec is not None:
            if spec.get("error") or not spec.get("type"):
                st.warning(spec.get("error") or "Could not plan a chart for this table.")
            else:
                try:
                    fig = draw_chart(result, spec)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"{spec['type']} chart - hover to see exact values")
                except Exception as e:
                    st.error(f"Could not draw the chart: {e}")

if st.session_state.get("api_key"):
    forget_key_button()
st.markdown('<div class="dv-foot">DataViz — powered by Gemini</div>',
            unsafe_allow_html=True)

