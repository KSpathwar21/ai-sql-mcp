import streamlit as st
import pandas as pd
from core.db import connect_db
from core.schema import extract_schema
from core.agent import run_agent

st.title("🧠 MCP AI SQL Assistant")

st.sidebar.header("Database Connection")

host = st.sidebar.text_input("Host", "localhost")
user = st.sidebar.text_input("Username", "root")
password = st.sidebar.text_input("Password", type="password")
database = st.sidebar.text_input("Database")

if st.sidebar.button("Connect"):
    try:
        conn = connect_db(host, user, password, database)
        st.session_state["conn"] = conn
        st.session_state["schema"] = extract_schema(conn)
        st.success("Connected successfully")
    except Exception as e:
        st.error(str(e))

if "conn" in st.session_state:

    question = st.text_area("Ask your question")

    if st.button("Ask AI"):

        with st.spinner("Thinking..."):
            sql_query, result, explanation = run_agent(
                question,
                st.session_state["schema"],
                st.session_state["conn"]
            )

        st.subheader("Generated SQL")
        st.code(sql_query, language="sql")

        st.subheader("Query Result")
        st.dataframe(pd.DataFrame(result))

        st.subheader("AI Explanation")
        st.write(explanation)