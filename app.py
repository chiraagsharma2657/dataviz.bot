"""Streamlit entry point: upload a CSV, ask a question, get a table and a chart."""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from querybot.charts import draw_chart
from querybot.data import normalize_dates, run_query, to_table_name
from querybot.llm import build_model, parse_chart_reply, reply_text, strip_fences
from querybot.prompts import chart_prompt, sql_prompt

load_dotenv()

st.set_page_config(page_title="QueryBot", page_icon="📊", layout="wide")


@st.cache_resource
def get_model():
    return build_model()


try:
    model = get_model()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

st.title("QueryBot: Ask Questions About Your Data")

# ---------------------------------------------------------------- 1. Upload
file = st.file_uploader("Upload a CSV file", type=["csv"])

df = None
date_cols = []
if file is not None:
    df = pd.read_csv(file)
    df, date_cols = normalize_dates(df)

    st.subheader("Preview")
    st.write("File name", file.name)
    st.dataframe(df.sample(min(10, len(df))))
    st.caption(f"{len(df)} row(s), {len(df.columns)} column(s)")
    if date_cols:
        st.caption("Date columns normalised to YYYY-MM-DD: " + ", ".join(date_cols))

    database = st.text_input(
        "Database name",
        value=f"{to_table_name(file.name)}_db",
        key=f"db_{file.name}",
    )

# ------------------------------------------------------------------ 2. Ask
if df is None:
    st.info("Upload a CSV file to start asking questions.")
    st.stop()

st.subheader("Ask a question")
question = st.text_input(
    "What do you want to see from this dataset?",
    placeholder="e.g. Top 10 cities by total sales",
    key="question",
)

# Only call the model when the question actually changed, so that toggling the
# chart options below does not re-run the query on every Streamlit rerun.
if question and st.session_state.get("answered_question") != question:
    table = to_table_name(file.name)

    with st.spinner("Building your query..."):
        response = model.invoke(
            sql_prompt(database, table, df, date_cols, question)
        )

    query = strip_fences(reply_text(response))
    st.session_state["answered_question"] = question
    st.session_state["query"] = query
    st.session_state["result"] = None
    st.session_state["error"] = None
    st.session_state["chart_spec"] = None

    if query.lower().startswith("select"):
        try:
            st.session_state["result"] = run_query(df, table, query)
        except Exception as e:
            st.session_state["error"] = f"Could not run the query on the uploaded data: {e}"

# --------------------------------------------------------------- 3. Result
query = st.session_state.get("query")
result = st.session_state.get("result")

if query:
    st.subheader("Query")
    st.code(query, language="sql")

    if not query.lower().startswith("select"):
        st.warning(query)
    elif st.session_state.get("error"):
        st.error(st.session_state["error"])

if result is not None:
    st.subheader("Result")
    st.dataframe(result)
    st.caption(f"{len(result)} row(s)")

    # ------------------------------------------------------- 4. Optional chart
    st.divider()
    if result.empty:
        st.info("Nothing to visualize: the query returned no rows.")
    elif st.checkbox("Visualize this result", key="want_chart"):
        chart_request = st.text_input(
            "How would you like it drawn? (optional)",
            placeholder="e.g. bar chart of sales by city, or leave blank to let the bot decide",
            key="chart_request",
        )

        if st.button("Create chart", key="make_chart"):
            with st.spinner("Designing your chart..."):
                reply = model.invoke(chart_prompt(
                    st.session_state.get("answered_question", ""),
                    result,
                    chart_request,
                ))
            st.session_state["chart_spec"] = parse_chart_reply(reply_text(reply))

        spec = st.session_state.get("chart_spec")
        if spec is not None:
            if spec.get("error") or not spec.get("type"):
                st.warning(spec.get("error") or "Could not plan a chart for this table.")
            else:
                try:
                    fig = draw_chart(result, spec)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"{spec['type']} chart - hover over the chart to see exact values")
                except Exception as e:
                    st.error(f"Could not draw the chart: {e}")
