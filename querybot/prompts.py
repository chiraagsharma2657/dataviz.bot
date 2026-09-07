"""The two prompts the app sends: one for SQL, one for the chart spec."""

import re

from .charts import CHART_TYPES
from .data import quote


def sql_prompt(database, table, df, date_cols, question):
    """Build the SQL-generation prompt from the uploaded dataframe."""
    columns = list(df.columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)
    text_cols = [c for c in columns
                 if c not in numeric_cols and c not in date_cols]

    example_measure = numeric_cols[0] if numeric_cols else columns[0]
    example_group = text_cols[0] if text_cols else columns[0]
    example_alias = "total_" + re.sub(r"\W+", "_", example_measure).lower()
    example_date = date_cols[0] if date_cols else None

    date_example = ""
    if example_date:
        date_example = f"""
Example 2 (extracting a year - use strftime, never YEAR()):
Question: Total {example_measure} per year

Answer:
SELECT CAST(strftime('%Y', {quote(example_date)}) AS INTEGER) AS year,
       SUM({quote(example_measure)}) AS {example_alias}
FROM {table}
GROUP BY year
ORDER BY year;

Example 3 (filtering to one year - note the CAST, without it you get 0 rows):
Question: All records from 2025

Answer:
SELECT *
FROM {table}
WHERE CAST(strftime('%Y', {quote(example_date)}) AS INTEGER) = 2025;
"""

    return f"""
You are an expert MySQL query generator.

Your task is to convert the user's question into a valid MySQL query only.

Database Name:
{database}

Table Name:
{table}

Available Columns:
{chr(10).join(columns)}

Numeric Columns:
{", ".join(numeric_cols) or "none"}

Categorical / Text Columns:
{", ".join(text_cols) or "none"}

Date Columns (already cleaned to the text format YYYY-MM-DD):
{", ".join(date_cols) or "none"}

Rules:
1. Always generate valid MySQL syntax.
2. Always query from the table {table}.
3. Never use the database name as the table name.
4. Always wrap table and column names containing spaces with backticks (`).
5. Do not invent tables or columns. Only the columns listed above exist.
6. Use MySQL-compatible functions only, except for dates - see rule 7.
7. DATES: every date column listed above is TEXT in YYYY-MM-DD form. The engine
   does not support YEAR(), MONTH(), DAY() or DATE_FORMAT() - always use
   strftime('%Y', col) for the year, '%m' month, '%d' day, '%Y-%m' year-month.
   strftime() returns TEXT, and TEXT never equals a bare number, so
   `strftime('%Y', col) = 2025` silently matches NOTHING. Every time you compare
   strftime() to a number you MUST cast it:
       WHERE CAST(strftime('%Y', col) AS INTEGER) = 2025
   Cast the same way when you SELECT a year or month as a number, and order by
   the alias. To filter a whole year, a plain string range is simplest and
   fastest: WHERE col >= '2025-01-01' AND col <= '2025-12-31'.
8. Use LIMIT whenever the user asks for top/bottom records.
9. Give every aggregated or computed column a simple snake_case alias
   (no spaces, no backticks), so the result table is easy to read and plot.
10. The user may mention a chart, graph or plot in their question. That is
    handled separately - IGNORE any visualization wording and answer only the
    data part of the question. Still SELECT the columns such a chart would need
    (the grouping column and the measure), and keep the row count reasonable.
11. If the user asks for columns that do not exist, return:
    "Invalid column name."
12. If the user asks anything unrelated to SQL or this database, return:
    "Please ask only SQL-related questions."
13. Return ONLY the SQL query. No explanations, no markdown, no code fences.

Example 1:
Question: Top 10 {example_group} by total {example_measure}

Answer:
SELECT {quote(example_group)},
       SUM({quote(example_measure)}) AS {example_alias}
FROM {table}
GROUP BY {quote(example_group)}
ORDER BY {example_alias} DESC
LIMIT 10;
{date_example}
USER QUESTION:
{question}
"""


def chart_prompt(question, result, chart_request):
    """Ask the model how to plot the table the user already has in front of them."""
    numeric_cols = list(result.select_dtypes(include="number").columns)
    text_cols = [c for c in result.columns if c not in numeric_cols]
    return f"""
You are a data visualization planner.

The user already ran a query and is looking at the RESULT TABLE below.
Now they want that table drawn as a chart. Decide how to plot it.

Original question that produced the table:
{question}

Result table columns:
{", ".join(result.columns)}

Numeric columns in the result:
{", ".join(numeric_cols) or "none"}

Categorical / text columns in the result:
{", ".join(text_cols) or "none"}

Number of rows in the result: {len(result)}

First rows of the result:
{result.head(5).to_string(index=False)}

The user's chart request:
{chart_request or "(no specific request - choose the best chart for this table)"}

Rules:
1. Allowed chart types: {", ".join(CHART_TYPES)}.
2. "x", "y" and "hue" MUST be column names from the result table above,
   spelled exactly. Never invent a column and never use a column of the
   original dataset that is not in the result table.
3. If the user names a chart type ("bar chart", "line graph", "pie chart",
   "scatter plot", "histogram", "box plot", "heatmap"), honour that choice as
   long as the result columns allow it.
4. If they do not name a type, choose a sensible default:
   - category vs one numeric measure -> "bar"
   - a date/time or ordered sequence vs a measure -> "line"
   - two numeric columns -> "scatter"
   - distribution of one numeric column -> "hist"
   - spread of a numeric column across categories -> "box"
   - share of a whole / percentage split -> "pie"
   - two categories crossed with one measure -> "heatmap"
5. Field usage per type:
   - bar / line / box: "x" = category or time, "y" = numeric measure,
     "hue" = optional second category, otherwise null.
   - scatter: "x" and "y" both numeric, "hue" optional category.
   - hist: "x" = numeric column, "y" = null, "hue" = optional category.
   - pie: "x" = label column, "y" = numeric column, "hue" = null.
   - heatmap: "x" = column category, "y" = row category, "hue" = numeric value.
6. Always give the chart a short "title".
7. If the requested chart is impossible with these columns, explain why in
   "error" and set "type" to null.

Return ONLY this JSON object, no markdown, no code fences, no explanation:
{{"type": "...", "x": "...", "y": "...", "hue": null, "title": "...", "error": null}}
"""
