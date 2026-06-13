import json
import pandas as pd
from google import genai
from utils.config import GEMINI_API_KEY
from core.memory import add_to_memory, get_memory

# Create client using API key
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3-flash-preview"   # FREE + supported

def execute_sql_tool(connection, query):
    if not query.lower().startswith("select"):
        raise Exception("Only SELECT queries allowed")

    df = pd.read_sql(query, connection)
    return df.to_dict(orient="records")


def generate_sql(question, schema):
    history = get_memory()
    history_text = ""
    for h in history:
        history_text += f"""
Previous Question: {h['question']}
SQL: {h['sql']}
"""
    prompt = f"""
You are an AI Data Analyst assistant.

Database Schema:
{schema}

Conversation History:
{history_text}

Rules:
- Perform analysis based on the question and database schema
- Use the execute_sql tool to run SQL queries on the database
- Always use the execute_sql tool to get data, never make up results
- Only generate SELECT queries
- Return only raw SQL
- No markdown
- No explanation

User Question:
{question}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


def explain_result(question, result):
    prompt = f"""
User asked: {question}

Query result:
{json.dumps(result)}

Explain clearly in simple English But as a Data Analyst would.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text.strip()


def run_agent(question, schema, connection):
    sql_query = generate_sql(question, schema)
    result = execute_sql_tool(connection, sql_query)
    explanation = explain_result(question, result)

    add_to_memory(question, sql_query, result, explanation)

    return sql_query, result, explanation