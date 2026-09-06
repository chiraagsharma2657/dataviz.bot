"""Loading, cleaning and querying the uploaded dataset."""

import os
import re
import sqlite3
import warnings

import pandas as pd


def to_table_name(file_name):
    """Turn 'Shipment Data.csv' into a safe MySQL table name."""
    stem = os.path.splitext(os.path.basename(file_name))[0]
    name = re.sub(r"\W+", "_", stem).strip("_").lower()
    return name or "uploaded_data"


def quote(col):
    """Backtick a column name only when it needs it."""
    return f"`{col}`" if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", col) else col


def normalize_dates(df):
    """Convert every date-like column to plain YYYY-MM-DD text.

    CSVs arrive with all sorts of date formats (05/06/2024, 6-May-24,
    2024/05/06, timestamps...). SQLite has no date type and its strftime()
    only understands ISO strings, so anything else silently returns NULL.
    Normalising once here means the rest of the app - the prompt, the SQL and
    the charts - only ever sees one format.

    Returns the converted dataframe and the list of columns that were changed.
    """
    df = df.copy()
    converted = []

    for col in df.columns:
        series = df[col]

        # Already a real datetime from pandas' own CSV parsing.
        if pd.api.types.is_datetime64_any_dtype(series):
            df[col] = series.dt.strftime("%Y-%m-%d")
            converted.append(col)
            continue

        # Only text columns are worth sniffing; numbers stay numbers so we
        # never turn an ID or a year count into a date. (pandas 3 stores text
        # as "str" dtype, older versions as "object", so allow both.)
        if not (pd.api.types.is_object_dtype(series)
                or pd.api.types.is_string_dtype(series)):
            continue

        sample = series.dropna()
        if sample.empty or not sample.map(type).eq(str).all():
            continue

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")

        # Only accept the column if nearly every non-empty value parsed, so a
        # stray date-looking string in a text column does not convert it.
        non_null = series.notna().sum()
        if non_null and parsed.notna().sum() / non_null >= 0.9:
            df[col] = parsed.dt.strftime("%Y-%m-%d")
            converted.append(col)

    return df, converted


def run_query(df, table, query):
    """Run the generated SQL against the uploaded data."""
    conn = sqlite3.connect(":memory:")
    try:
        df.to_sql(table, conn, index=False)
        return pd.read_sql_query(query.rstrip(";"), conn)
    finally:
        conn.close()
