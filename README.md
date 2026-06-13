# AI SQL MCP Assistant

A natural language to SQL assistant powered by Google Gemini AI. Users connect to a MySQL database, ask questions in plain English, and the app generates SQL, executes it, and returns results with an AI-generated explanation.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Setup & Installation](#setup--installation)
- [How It Works](#how-it-works)
- [File Reference](#file-reference)
- [Data Flow](#data-flow)
- [Known Limitations](#known-limitations)

---

## Project Structure

```
ai-sql-mcp/
├── app.py                  # Streamlit UI — entry point
├── .env                    # Environment variables (GEMINI_API_KEY)
├── requirements.txt        # Python dependencies
├── core/
│   ├── __init__.py
│   ├── agent.py            # AI pipeline orchestrator
│   ├── db.py               # MySQL connection
│   ├── memory.py           # In-session conversation memory
│   ├── schema.py           # DB schema extractor
│   └── tools.py            # Tool/function schema definition
└── utils/
    └── config.py           # Loads env variables via python-dotenv
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  app.py  (Streamlit UI)              │
│                                                      │
│  Sidebar: DB credentials  →  Connect button         │
│  Main:    Question input  →  Ask AI button          │
│                                                      │
│  st.session_state["conn"]    → persists connection  │
│  st.session_state["schema"]  → persists DB schema   │
└────────────────────┬────────────────────────────────┘
                     │  run_agent(question, schema, conn)
                     ▼
┌─────────────────────────────────────────────────────┐
│              core/agent.py  (Orchestrator)           │
│                                                      │
│  1. get_memory()        → last 3 Q&A pairs          │
│  2. generate_sql()      → Gemini → SQL string       │
│  3. execute_sql_tool()  → MySQL  → result rows      │
│  4. explain_result()    → Gemini → explanation text │
│  5. add_to_memory()     → save to in-memory list    │
└──┬──────────────────────────────────────────────────┘
   │
   ├── core/db.py        MySQL connection wrapper
   ├── core/schema.py    SHOW TABLES + DESCRIBE → schema string
   ├── core/memory.py    In-memory list, sliding window of 3
   ├── core/tools.py     OpenAI-format tool schema (defined, not wired)
   └── utils/config.py   Loads GEMINI_API_KEY from .env
```

---

## Setup & Installation

### Prerequisites
- Python 3.9+
- MySQL server running locally or remotely
- Google Gemini API key

### Install dependencies

```bash
pip install streamlit mysql-connector-python pandas python-dotenv google-genai
```

> Note: `requirements.txt` lists `openai` which is not used. Install `google-genai` manually as it is missing from the file.

### Configure environment

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Connect to database

Fill in the sidebar form:
- **Host** — e.g. `localhost`
- **Username** — e.g. `root`
- **Password** — your MySQL password
- **Database** — the database name to query

Click **Connect**. On success, the schema is extracted and stored in session state.

---

## How It Works

### Step 1 — Schema Extraction (`core/schema.py`)

After connecting, `extract_schema()` runs:
```sql
SHOW TABLES;
DESCRIBE {table};   -- for each table
```
This builds a compact schema string fed into every LLM prompt:
```
Table users(id, name, email, created_at)
Table orders(id, user_id, amount, status)
```

### Step 2 — SQL Generation (`core/agent.py:generate_sql`)

A prompt is built with three components:
1. The database schema (column names per table)
2. The last 3 Q&A pairs from memory (for follow-up question support)
3. The user's natural language question

Gemini returns a raw SQL string. Markdown code fences (` ```sql ``` `) are stripped before use.

### Step 3 — SQL Execution (`core/agent.py:execute_sql_tool`)

- Validates the query starts with `SELECT` — blocks `DROP`, `DELETE`, `UPDATE`, etc.
- Executes via `pd.read_sql(query, connection)`
- Returns `list[dict]` with `orient="records"` format

### Step 4 — Explanation (`core/agent.py:explain_result`)

A second Gemini call receives the original question and the raw result JSON. It returns a plain-English explanation written from a Data Analyst's perspective.

### Step 5 — Memory (`core/memory.py`)

Each interaction is stored in a module-level list:
```python
{ "question": ..., "sql": ..., "result": ..., "explanation": ... }
```
`get_memory()` returns only the last 3 entries. This sliding window keeps the prompt size manageable while supporting follow-up questions.

---

## File Reference

### `app.py`

| Element | Purpose |
|---------|---------|
| `st.sidebar` form | DB connection inputs |
| `Connect` button | Initializes conn + schema in session state |
| `st.session_state` | Maintains DB connection and schema across Streamlit reruns |
| `run_agent()` | Returns `(sql_query, result, explanation)` |
| `st.code(sql_query, language="sql")` | Syntax-highlighted SQL display |
| `st.dataframe(pd.DataFrame(result))` | Tabular result display |

---

### `core/agent.py`

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `generate_sql(question, schema)` | NL question, schema string | SQL string | Prompts Gemini with schema + memory + question |
| `execute_sql_tool(connection, query)` | MySQL conn, SQL string | `list[dict]` | SELECT guard + executes query |
| `explain_result(question, result)` | NL question, result list | Explanation string | Second Gemini call for plain-English explanation |
| `run_agent(question, schema, connection)` | NL question, schema, conn | `(sql, result, explanation)` | Orchestrates all steps end-to-end |

**LLM Model used:** `gemini-3-flash-preview` via `google.genai.Client`

---

### `core/db.py`

```python
def connect_db(host, user, password, database) -> MySQLConnection
```

Thin wrapper around `mysql-connector-python`. Returns a raw connection object. No pooling.

---

### `core/schema.py`

```python
def extract_schema(connection) -> str
```

Extracts table and column names using `SHOW TABLES` + `DESCRIBE`. Returns a compact string like:
```
Table orders(id, user_id, amount, status)
```

---

### `core/memory.py`

```python
memory = []                                         # module-level, session-scoped
def add_to_memory(question, sql, result, explanation)
def get_memory() -> list                            # returns last 3 entries
```

In-memory conversation store. Resets on server restart. Provides context for follow-up questions by injecting prior Q&A into the next prompt.

---

### `core/tools.py`

Defines an OpenAI-compatible function-calling schema for `execute_sql`:

```python
{
  "type": "function",
  "function": {
    "name": "execute_sql",
    "description": "Execute a SELECT SQL query on MySQL database",
    "parameters": { "type": "object", "properties": { "query": { "type": "string" } } }
  }
}
```

> This schema is defined but not currently wired into the agent. The agent calls `execute_sql_tool()` directly. The intent was to use Gemini's native function-calling so the model decides when to execute SQL — a more autonomous agent pattern.

---

### `utils/config.py`

```python
load_dotenv(BASE_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
```

Uses `pathlib.Path` to resolve the `.env` path relative to the project root, regardless of where the script is invoked from.

---

## Data Flow

```
User types question
        │
        ▼
run_agent(question, schema, connection)
        │
        ├─► get_memory()         → last 3 Q&A pairs (sliding window)
        │
        ├─► generate_sql()       → Prompt: schema + history + question
        │       └─► Gemini API   → raw SQL string (markdown stripped)
        │
        ├─► execute_sql_tool()   → SELECT-only guard + pd.read_sql()
        │       └─► MySQL DB     → list of row dicts
        │
        ├─► explain_result()     → Prompt: question + result JSON
        │       └─► Gemini API   → plain English explanation
        │
        └─► add_to_memory()      → append to in-memory list
                │
                ▼
        return (sql, result, explanation)
                │
                ▼
        Streamlit renders:
          st.code()       → SQL with syntax highlighting
          st.dataframe()  → result table
          st.write()      → AI explanation
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | latest | Web UI framework |
| `mysql-connector-python` | latest | MySQL database driver |
| `pandas` | latest | SQL result → DataFrame → dict |
| `python-dotenv` | latest | Load `.env` file |
| `google-genai` | latest | Gemini AI API client (install manually) |
| `openai` | listed | Not used — leftover from earlier version |

---

## Known Limitations

| Issue | Impact | Suggested Fix |
|-------|--------|---------------|
| Memory resets on restart | No cross-session history | Use Redis or a database for persistence |
| `tools.py` not wired up | No autonomous tool-calling | Pass tool schema to Gemini's function-calling API |
| `google-genai` missing from `requirements.txt` | Manual install required | Add to `requirements.txt` |
| No DB connection pooling | New connection per session | Use SQLAlchemy with a connection pool |
| Schema lacks FK/index info | Suboptimal JOIN generation | Include foreign key relationships in schema extraction |
| No response streaming | Full wait before display | Use Gemini streaming API for better UX |
| API key committed to `.env` in repo | Security risk | Use a secrets manager or `.gitignore` the `.env` file |
