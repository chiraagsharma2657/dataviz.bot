"""Date handling: normalisation, and repairing the SQL the model writes.

The bug these cover: strftime() returns TEXT, so a query like
`WHERE strftime('%Y', d) = 2025` matched nothing and produced an empty
dataframe with no error to explain it.
"""

import pandas as pd
import pytest

from dataviz.data import normalize_dates, run_query
from dataviz.sql import is_select, repair_sql

ROWS = {
    "Order ID": [1, 2, 3, 4],
    "Sales": [100, 200, 300, 400],
}


def frame(dates):
    return pd.DataFrame({**ROWS, "Order Date": dates})


@pytest.mark.parametrize("dates", [
    ["01/15/2025", "03/22/2025", "07/09/2024", "11/30/2025"],   # US slashes
    ["2025-01-15", "2025-03-22", "2024-07-09", "2025-11-30"],   # already ISO
    ["15-Jan-2025", "22-Mar-2025", "09-Jul-2024", "30-Nov-2025"],  # named month
    ["2025/01/15", "2025/03/22", "2024/07/09", "2025/11/30"],   # ISO slashes
])
def test_dates_normalise_to_iso(dates):
    df, date_cols = normalize_dates(frame(dates))
    assert date_cols == ["Order Date"]
    assert df["Order Date"].tolist() == [
        "2025-01-15", "2025-03-22", "2024-07-09", "2025-11-30"
    ]


def test_numeric_column_is_not_mistaken_for_a_date():
    df = pd.DataFrame({"year_count": [2025, 1999, 2024], "n": [1, 2, 3]})
    _, date_cols = normalize_dates(df)
    assert date_cols == []


def test_text_column_with_one_stray_date_is_left_alone():
    df = pd.DataFrame({"note": ["hello", "world", "2025-01-01", "again", "more"]})
    _, date_cols = normalize_dates(df)
    assert date_cols == []


@pytest.mark.parametrize("query,expected", [
    # The original bug: text compared to a bare number.
    ("SELECT * FROM t WHERE strftime('%Y', `Order Date`) = 2025", 3),
    # MySQL functions the model reaches for, which SQLite does not have.
    ("SELECT * FROM t WHERE YEAR(`Order Date`) = 2025", 3),
    ("SELECT * FROM t WHERE MONTH(`Order Date`) = 3", 1),
    ("SELECT * FROM t WHERE DATE_FORMAT(`Order Date`, '%Y') = 2025", 3),
    # Ranges, not just equality.
    ("SELECT * FROM t WHERE YEAR(`Order Date`) >= 2025", 3),
    ("SELECT * FROM t WHERE YEAR(`Order Date`) != 2025", 1),
])
def test_repaired_queries_return_rows(query, expected):
    df, _ = normalize_dates(frame(["01/15/2025", "03/22/2025", "07/09/2024", "11/30/2025"]))
    assert len(run_query(df, "t", repair_sql(query))) == expected


@pytest.mark.parametrize("query", [
    # Already correct - repair must not double-cast or otherwise disturb these.
    "SELECT * FROM t WHERE CAST(strftime('%Y', `Order Date`) AS INTEGER) = 2025",
    "SELECT * FROM t WHERE strftime('%Y', `Order Date`) = '2025'",
    "SELECT * FROM t WHERE `Order Date` >= '2025-01-01'",
    "SELECT strftime('%Y-%m', `Order Date`) AS ym, SUM(Sales) AS t FROM t GROUP BY ym",
])
def test_correct_queries_are_untouched(query):
    assert repair_sql(query) == query


def test_repair_leaves_string_literals_alone():
    query = "SELECT * FROM t WHERE note = 'YEAR(x) = 2025'"
    assert repair_sql(query) == query


@pytest.mark.parametrize("query", [
    "SELECT * FROM t",
    "WITH ranked AS (SELECT 1 AS a) SELECT * FROM ranked",   # the CTE case
    "  \n-- a comment\nSELECT 1",
    "/* block */ WITH x AS (SELECT 1) SELECT * FROM x",
    "SELECT * FROM t WHERE note = 'DROP TABLE x'",           # keyword in a string
])
def test_read_only_queries_are_allowed(query):
    assert is_select(query)


@pytest.mark.parametrize("query", [
    "",
    "Invalid column name.",
    "Please ask only SQL-related questions.",
    "DROP TABLE t",
    "UPDATE t SET a = 1",
    "WITH a AS (SELECT 1) DELETE FROM t",   # a write hiding behind a CTE
    "SELECT 1; DROP TABLE t",               # a write appended to a read
])
def test_writes_and_refusals_are_rejected(query):
    assert not is_select(query)


def test_cte_with_window_function_runs():
    """The "top item per group" shape the model reaches for - a CTE, which the
    old leading-SELECT check rejected as if the model had refused."""
    df = pd.DataFrame({
        "country": ["IN", "IN", "US", "US"],
        "product": ["A", "B", "A", "B"],
        "qty": [5, 9, 7, 2],
    })
    query = (
        "WITH ranked AS (SELECT country, product, SUM(qty) AS total, "
        "ROW_NUMBER() OVER (PARTITION BY country ORDER BY SUM(qty) DESC) AS rnk "
        "FROM t GROUP BY country, product) "
        "SELECT country, product, total FROM ranked WHERE rnk = 1"
    )
    assert is_select(query)
    out = run_query(df, "t", repair_sql(query))
    assert out["product"].tolist() == ["B", "A"]
    assert out["total"].tolist() == [9, 7]


def test_grouping_by_year_still_works():
    df, _ = normalize_dates(frame(["01/15/2025", "03/22/2025", "07/09/2024", "11/30/2025"]))
    query = repair_sql(
        "SELECT YEAR(`Order Date`) AS year, SUM(Sales) AS total "
        "FROM t GROUP BY year ORDER BY year"
    )
    out = run_query(df, "t", query)
    assert out["year"].tolist() == [2024, 2025]
    assert out["total"].tolist() == [300, 700]

