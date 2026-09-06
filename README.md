# QueryBot

Upload a CSV, ask a question in plain English, and get back the SQL, the result
table, and an interactive chart.

The app sends only your column names and a five-row sample to the model — it
writes the SQL, but the query runs locally against an in-memory SQLite copy of
your file. Your data never leaves the machine as a whole.

## How it works

1. **Upload** — the CSV is read with pandas and every date-like column is
   normalised to `YYYY-MM-DD`, so SQLite's `strftime()` can actually read it.
2. **Ask** — your question plus the schema goes to Gemini, which returns a
   single `SELECT`.
3. **Run** — the query executes against an in-memory SQLite table.
4. **Visualize** (optional) — the model picks a chart type and the columns to
   map onto it; Plotly draws it.

## Setup

```bash
git clone <your-repo-url>
cd dataviz.bot

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

Add your API key:

```bash
cp .env.example .env          # then edit .env and paste your key
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey).

## Run

```bash
streamlit run app.py
```

Then open http://localhost:8501.

## Project layout

```
app.py               Streamlit UI — upload, ask, show result, draw chart
querybot/
  data.py            CSV cleaning, table naming, running SQL on the dataframe
  charts.py          Chart spec -> Plotly figure (bar, line, scatter, hist,
                     box, heatmap, pie)
  llm.py             Model setup and parsing model replies
  prompts.py         The SQL prompt and the chart-planning prompt
requirements.txt
.env.example         Copy to .env and add your key
```

## Notes

- `.env` is gitignored. Never commit a real key.
- Only `SELECT` statements are executed; anything else is shown to you as a
  warning instead of run.
