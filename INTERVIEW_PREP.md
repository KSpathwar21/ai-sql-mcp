# Interview Preparation — AI SQL MCP Assistant

---

## Table of Contents

- [Project Introduction](#project-introduction)
- [Basic Questions](#basic-questions)
- [Streamlit & UI Layer](#streamlit--ui-layer)
- [Database & Connection](#database--connection)
- [AI & LLM Layer](#ai--llm-layer)
- [Memory & Context](#memory--context)
- [Security](#security)
- [Architecture & Design](#architecture--design)
- [Improvements & What You Would Do Differently](#improvements--what-you-would-do-differently)
- [Scenario-Based Questions](#scenario-based-questions)

---

## Project Introduction

### Q: Tell me about this project in 2-3 sentences.

> "I built a natural language to SQL assistant using Streamlit and Google Gemini AI. Users connect to a MySQL database, ask questions in plain English, and the app generates SQL, executes it, and returns results with an AI-generated explanation. The core idea was to make database querying accessible without needing SQL knowledge."

---

### Q: What problem does this project solve?

> "Most business users can't write SQL but need to query databases for insights. This project removes that barrier — they just type a plain English question like 'show me top 5 customers by revenue this month' and the AI handles the SQL generation, execution, and explanation automatically."

---

### Q: Walk me through the overall flow of the application.

> "When the user fills in DB credentials and clicks Connect, the app opens a MySQL connection and extracts the schema — table names and column names. That schema is stored in Streamlit session state.
>
> When the user asks a question, three things happen in sequence: Gemini generates SQL using the schema and conversation history as context, the SQL is executed against the live database, and then Gemini makes a second call to explain the result in plain English. All three outputs are shown on the UI."

---

## Basic Questions

### Q: What tech stack did you use and why?

| Technology | Why Used |
|------------|---------|
| Streamlit | Rapid UI with minimal frontend code — ideal for data apps |
| Google Gemini | Free tier available, strong SQL generation capability |
| MySQL + mysql-connector-python | Widely used relational DB, straightforward Python driver |
| Pandas | Best tool for converting SQL results to structured formats |
| python-dotenv | Clean way to manage API keys without hardcoding |

---

### Q: Why Streamlit over Flask or FastAPI?

> "Streamlit is purpose-built for data applications. It turns Python scripts into interactive UIs with minimal code — no HTML, CSS, or JavaScript needed. Flask or FastAPI would be better for production APIs or complex routing, but for a data assistant prototype, Streamlit let me focus entirely on the AI and database logic."

---

### Q: Why Google Gemini over OpenAI?

> "Gemini has a generous free tier which made it practical for prototyping. The API interface is similar to OpenAI — you send a prompt and get a response. The `requirements.txt` still lists `openai` as a leftover from the initial version, which is a gap I'd clean up."

---

## Streamlit & UI Layer

### Q: How does Streamlit maintain state across button clicks?

> "Streamlit reruns the entire script from top to bottom on every user interaction. Without state management, all variables would reset on each rerun. `st.session_state` is a dictionary that persists across reruns for that browser tab — so the DB connection and schema are stored there once on Connect and reused for every subsequent query."

---

### Q: What is stored in session state and why?

```python
st.session_state["conn"]    # MySQL connection object
st.session_state["schema"]  # extracted schema string
```

> "`conn` is stored so the app doesn't reconnect to MySQL on every button click — opening a connection is expensive. `schema` is stored so we don't re-run `SHOW TABLES` and `DESCRIBE` on every query. Both are set once when Connect is clicked and reused throughout the session."

---

### Q: What happens if the user opens the app in two browser tabs?

> "Each tab gets its own `st.session_state` — they are completely isolated. So each tab creates its own separate MySQL connection. There's no shared state between tabs. This also means two users on different machines each hold their own connection, which doesn't scale well."

---

## Database & Connection

### Q: How is the database connection maintained across queries?

> "A single connection is created when the user clicks Connect using `mysql.connector.connect()`. That connection object is stored in `st.session_state["conn"]`. Every time the user asks a question, the same connection object is passed into `run_agent()` and used by `pd.read_sql()` — no new connection is opened per query."

---

### Q: What are the limitations of this connection approach?

> "Three main limitations:
> 1. No reconnect logic — if MySQL closes the connection due to idle timeout (default 8 hours) or a server restart, the next query fails with an error and the user has to manually click Connect again.
> 2. No connection pooling — each browser tab holds one connection, so 100 users means 100 open connections to MySQL simultaneously.
> 3. No graceful cleanup — if the user closes the browser tab, the connection isn't explicitly closed, leaving it open until MySQL's timeout kicks in."

---

### Q: How does `extract_schema()` work?

```python
cursor.execute("SHOW TABLES")          # get all table names
cursor.execute(f"DESCRIBE {table}")    # get columns for each table
schema += f"Table {table}({col_names})"
```

> "It runs `SHOW TABLES` to get all table names, then `DESCRIBE` on each table to get column names. These are assembled into a compact string like `Table orders(id, user_id, amount, status)`. This string is injected into every LLM prompt so Gemini knows the database structure."

---

### Q: Why does the schema only include column names and not data types or foreign keys?

> "It was kept minimal to save prompt tokens. Column names are usually enough for basic SQL generation. However, this is a limitation — without foreign key information, the model can't infer table relationships accurately, which leads to poor or incorrect JOIN queries. In an improved version, I'd include data types and foreign key constraints."

---

## AI & LLM Layer

### Q: How does the SQL generation work?

> "A prompt is built with three components: the database schema, the last 3 Q&A pairs from memory, and the current question. This is sent to Gemini's `generate_content()` API. The response is a raw SQL string. We strip any markdown code fences like ` ```sql ``` ` that Gemini sometimes wraps around the output, then return the clean SQL."

---

### Q: Why are there two separate Gemini calls?

> "Separation of concerns. The first call is focused purely on generating valid SQL — the prompt is strict: no explanation, no markdown, just raw SQL. The second call is focused on explaining the result in plain English for a non-technical user. Mixing both tasks in one prompt tends to make the SQL less reliable, so splitting them gives better results for each."

---

### Q: What is prompt engineering and where did you apply it?

> "Prompt engineering is crafting the input to an LLM to get consistent, accurate output. I applied it in two places:
> 1. In `generate_sql()` — I explicitly told the model to return only raw SQL with no markdown, no explanation, and only SELECT queries. This prevents the model from adding conversational filler that would break the SQL execution.
> 2. In `explain_result()` — I told it to explain like a Data Analyst, which produces more domain-relevant explanations than a generic summary."

---

### Q: What is `tools.py` and why is it not used?

> "`tools.py` defines an OpenAI-compatible function-calling schema for `execute_sql`. The original design intent was to use **LLM tool calling** — where the model itself decides when to call `execute_sql` as part of its reasoning. Instead, the current implementation hardcodes a linear pipeline: always generate SQL, always execute, always explain.
>
> Tool calling would make it more agentic — the model could reason across multiple steps, decide to run a query, check the result, then run a follow-up query if needed. I'd wire this up properly in an improved version."

---

### Q: What is the difference between the current approach and a true agentic approach?

| Current (Linear Pipeline) | Agentic (Tool Calling) |
|--------------------------|----------------------|
| Always: generate → execute → explain | LLM decides when and how many times to call tools |
| Fixed 3-step flow | Dynamic, multi-step reasoning |
| Can't self-correct | Can detect empty results and retry with a different query |
| Simpler to debug | More powerful but harder to control |

---

## Memory & Context

### Q: How does conversation memory work?

> "After each interaction, the question, generated SQL, result, and explanation are appended to a module-level Python list. Before generating SQL for the next question, the last 3 entries from this list are fetched and injected into the prompt as conversation history. This lets the model handle follow-up questions like 'now sort that by date' without re-explaining the full context."

---

### Q: Why only keep the last 3 conversations?

> "LLMs have a context window limit — you can only send so many tokens per request. Keeping the full history would eventually overflow the context window and increase API cost. 3 is a practical balance: enough for follow-up questions, not so much that it bloats the prompt."

---

### Q: What is the biggest limitation of the current memory implementation?

> "It's in-memory and session-scoped — stored in a plain Python list at the module level. It resets every time the server restarts. There's no persistence across sessions, no per-user isolation in a multi-user setup, and it could theoretically mix conversation history between users if sessions overlap in the same process. For production, I'd use Redis or a database table keyed by session ID."

---

### Q: What is the difference between this memory and a vector database?

> "This memory does simple recency-based retrieval — always the last 3 entries regardless of relevance. A vector database like Pinecone or ChromaDB stores embeddings of past conversations and retrieves the most semantically similar ones. So if a user asks something related to a question from 20 interactions ago, a vector store would surface it; this implementation wouldn't."

---

## Security

### Q: How did you prevent SQL injection?

> "There are two layers. First, `execute_sql_tool()` checks that the query starts with `SELECT` — this blocks `DROP`, `DELETE`, `UPDATE`, and `INSERT` entirely. Second, the SQL is generated by the LLM from a natural language question, not by directly embedding user input into a SQL string, so classic string-interpolation injection doesn't apply here."

---

### Q: Is the SELECT-only check sufficient? Can it be bypassed?

> "It's a basic guard, not a full solution. A crafted prompt could theoretically get the LLM to generate something like `SELECT * FROM users; DROP TABLE users;` — a SQL injection via prompt injection. A proper implementation would use a read-only MySQL user that literally has no DELETE/DROP privileges at the database level, making the check redundant but keeping it as an extra layer of defense."

---

### Q: How is the API key managed?

> "It's stored in a `.env` file and loaded via `python-dotenv`. The `utils/config.py` uses `pathlib.Path` to resolve the `.env` path relative to the project root. However, the `.env` file is currently not in `.gitignore`, which means it could be accidentally committed — a serious security risk. In production, I'd use a secrets manager like AWS Secrets Manager or HashiCorp Vault."

---

## Architecture & Design

### Q: Why is the project split into `core/` and `utils/`?

> "`core/` contains the domain logic — everything specific to this application: the agent, DB connection, schema extraction, memory, and tool definitions. `utils/` contains infrastructure concerns that could be reused across any project — config loading, environment management. It's a separation of business logic from cross-cutting concerns."

---

### Q: What design pattern does `run_agent()` follow?

> "It's a **pipeline pattern** — a fixed sequence of steps where the output of one step feeds into the next: generate SQL → execute SQL → explain result. It's also loosely an **orchestrator pattern** — `run_agent()` doesn't do any of the work itself, it just calls and sequences the three specialized functions."

---

### Q: Is this a true MCP (Model Context Protocol) implementation?

> "Not fully. The name references MCP but the implementation is a simplified linear pipeline. A true MCP implementation would have the model dynamically invoking tools via a standardized protocol, with the model in control of when and how tools are called. The `tools.py` file hints at the intent, but it's not wired up. The current design is more accurately described as a prompt-chaining pipeline."

---

## Improvements & What You Would Do Differently

### 1. Connection Pooling

**Current problem:** Single raw connection per session, no reconnect logic.

**Improvement:**
```python
# Replace mysql.connector with SQLAlchemy engine
from sqlalchemy import create_engine

engine = create_engine(
    f"mysql+mysqlconnector://{user}:{password}@{host}/{database}",
    pool_size=5,
    pool_recycle=3600,   # reconnect after 1 hour
    pool_pre_ping=True   # test connection before use
)
st.session_state["engine"] = engine
```
**Why:** Handles timeouts automatically, supports multiple users, cleans up idle connections.

---

### 2. Persistent Memory with Session Isolation

**Current problem:** In-memory list resets on restart, no per-user isolation.

**Improvement:**
```python
# Use Redis with session ID as key
import redis
import json

r = redis.Redis()

def add_to_memory(session_id, question, sql, result, explanation):
    key = f"memory:{session_id}"
    history = json.loads(r.get(key) or "[]")
    history.append({"question": question, "sql": sql})
    r.set(key, json.dumps(history[-3:]), ex=3600)  # expires in 1 hour

def get_memory(session_id):
    key = f"memory:{session_id}"
    return json.loads(r.get(key) or "[]")
```
**Why:** Survives server restarts, isolates per user, automatically expires old sessions.

---

### 3. Wire Up Tool Calling (True Agent)

**Current problem:** Linear pipeline — can't self-correct or run multi-step reasoning.

**Improvement:** Pass `tools.py` schema to Gemini and let the model call `execute_sql` when it decides to.

```
User question
     │
     ▼
Gemini reasoning loop:
  ├── "I need data" → calls execute_sql tool
  ├── Sees empty result → reformulates query → calls tool again
  ├── Has enough data → generates explanation
  └── Returns final answer
```
**Why:** The model can handle cases like empty results, ambiguous questions, or multi-table queries that need intermediate steps.

---

### 4. Richer Schema Extraction

**Current problem:** Only table and column names — no data types, foreign keys, or sample data.

**Improvement:**
```python
# Include foreign keys
cursor.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE REFERENCED_TABLE_NAME IS NOT NULL
    AND TABLE_SCHEMA = %s
""", (database,))
```
**Why:** Foreign key info enables the LLM to generate correct JOINs. Data types prevent type mismatch errors in WHERE clauses.

---

### 5. Read-Only Database User

**Current problem:** The SELECT-only check in Python can be bypassed via prompt injection.

**Improvement:**
```sql
-- Create a read-only MySQL user
CREATE USER 'readonly_user'@'%' IDENTIFIED BY 'password';
GRANT SELECT ON database_name.* TO 'readonly_user'@'%';
```
**Why:** Enforces the restriction at the database level — even if a malicious SQL gets past the Python check, MySQL will reject it.

---

### 6. Fix `requirements.txt`

**Current problem:** `openai` is listed but unused. `google-genai` is missing.

**Fix:**
```
streamlit
mysql-connector-python
pandas
python-dotenv
google-genai
sqlalchemy
```

---

### 7. Streaming Responses

**Current problem:** User waits for the full Gemini response before seeing anything.

**Improvement:**
```python
response = client.models.generate_content_stream(
    model=MODEL_NAME,
    contents=prompt
)
for chunk in response:
    st.write(chunk.text)
```
**Why:** Better UX — user sees the explanation being written in real time rather than a blank spinner.

---

### 8. Add `.gitignore`

**Current problem:** `.env` file with API key could be committed to version control.

**Fix — create `.gitignore`:**
```
.env
__pycache__/
*.pyc
.streamlit/
```

---

## Scenario-Based Questions

### Q: A user asks "show me the same data but for last month" — how does your app handle it?

> "The memory module injects the last 3 Q&A pairs into the prompt. So the previous question and its generated SQL are visible to Gemini when processing this follow-up. Gemini can reference the previous SQL, modify the date filter, and return the updated query — without the user needing to repeat the full context."

---

### Q: What happens if Gemini generates invalid SQL?

> "Currently, `pd.read_sql()` would raise an exception which is unhandled in `run_agent()` — the error would bubble up and Streamlit would display it as a red error message. There's no retry logic. An improvement would be to catch the exception, send the error back to Gemini with the original question and ask it to fix the SQL, then retry — a self-healing loop."

---

### Q: What happens if the database has 100 tables?

> "The schema string would be very long — potentially thousands of tokens. This increases API cost and can push the prompt close to Gemini's context limit. A better approach would be to use embeddings to find the most relevant tables for the question and only include those in the prompt — semantic schema pruning."

---

### Q: How would you add support for PostgreSQL or SQLite?

> "The only MySQL-specific parts are `mysql.connector.connect()` in `db.py` and the `SHOW TABLES` / `DESCRIBE` commands in `schema.py`. I'd replace the connector with SQLAlchemy, which supports all major databases through a unified API. The schema extraction would use `INFORMATION_SCHEMA` queries which are mostly standard across databases."

---

### Q: How would you deploy this to production?

> "I'd containerize it with Docker, replace the raw connection with SQLAlchemy pooling, move the API key to a secrets manager, replace in-memory storage with Redis for session memory, add a read-only DB user, and deploy on a cloud platform like AWS or GCP behind an authentication layer so only authorized users can access it."
