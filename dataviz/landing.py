"""The landing page: what this is, and where the visitor's API key goes.

The key is held in st.session_state for the length of one browser session. It
is deliberately NOT written to .env or any other file: a hosted app is a single
process shared by everyone using it, so a key on disk is a key handed to the
next visitor. Session state is per-visitor and lives in memory only.
"""

import streamlit as st

from . import theme
from .llm import verify_key

KEY_URL = "https://aistudio.google.com/apikey"


def _hero():
    logo = theme.logo_data_uri()
    if logo:
        st.markdown(
            f'<div class="dv-hero"><img src="{logo}" alt="DataViz">'
            '<p class="dv-tagline">Ask your data anything. No SQL required.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="dv-hero"><h1>DataViz</h1></div>',
                    unsafe_allow_html=True)


def _features():
    st.markdown(
        '<div class="dv-features">'
        '<div class="dv-feature"><b>Plain English in</b>'
        '<span>Ask "top 10 cities by sales" and get the SQL written for you.</span></div>'
        '<div class="dv-feature"><b>Answers out</b>'
        '<span>The query runs on your file and returns a real table.</span></div>'
        '<div class="dv-feature"><b>Charts on request</b>'
        '<span>Turn any result into an interactive chart in one click.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def require_api_key():
    """Show the landing page until a working key is provided.

    Returns the key. Halts the script while the visitor is still on the page.
    """
    if st.session_state.get("api_key"):
        return st.session_state["api_key"]

    _hero()
    st.markdown('<hr class="dv-rule">', unsafe_allow_html=True)
    _features()

    st.markdown('<div class="dv-gate">', unsafe_allow_html=True)
    st.markdown('<div class="dv-step">Bring your own key</div>',
                unsafe_allow_html=True)
    st.markdown(
        "DataViz runs on Google's Gemini. Keys are free, take about a minute to "
        f"create, and each visitor uses their own — [get one here]({KEY_URL}).",
    )

    entered = st.text_input(
        "Google API key",
        type="password",
        placeholder="Paste your Gemini API key",
        key="api_key_input",
        label_visibility="collapsed",
    )

    if st.button("Start exploring", key="submit_key"):
        if not entered.strip():
            st.warning("Paste a key first.")
        else:
            with st.spinner("Checking your key..."):
                problem = verify_key(entered.strip())
            if problem:
                st.error(problem)
            else:
                st.session_state["api_key"] = entered.strip()
                st.rerun()

    st.markdown(
        '<p class="dv-privacy">Your key stays in this browser session only. '
        'It is never written to a file, never logged, and is gone when you '
        'close the tab. Your CSV is read in memory and never uploaded '
        'anywhere.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="dv-foot">DataViz — powered by Gemini</div>',
                unsafe_allow_html=True)
    st.stop()


def forget_key_button():
    """Let a visitor drop their key without closing the tab."""
    if st.button("Use a different key", key="forget_key"):
        for k in ("api_key", "answered_question", "query", "result",
                  "chart_spec", "error", "repaired"):
            st.session_state.pop(k, None)
        st.rerun()
