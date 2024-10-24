import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
import pandas as pd
import tempfile
from langchain_groq import ChatGroq

st.set_page_config(page_title="QueryEase-", page_icon="✿")
st.title("Chat with SQL DB")

# Upload file (SQLite, CSV, Excel)
uploaded_file = st.sidebar.file_uploader("Upload your SQLite, CSV, or Excel file", type=["db", "sqlite", "csv", "xlsx"])

# Set the Groq API key directly in the code
api_key = "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"

def convert_to_sqlite(file):
    conn = sqlite3.connect(":memory:")  # Create a temporary in-memory database
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
        df.to_sql('uploaded_data', conn, index=False, if_exists='replace')
    elif file.name.endswith('.xlsx'):
        df = pd.read_excel(file)
        df.to_sql('uploaded_data', conn, index=False, if_exists='replace')
    return conn

if uploaded_file is not None:
    if uploaded_file.name.endswith(".db") or uploaded_file.name.endswith(".sqlite"):
        db_uri = "USE_LOCALDB"
        dbfilepath = Path(uploaded_file.name)
        with open(dbfilepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        conn = sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
    elif uploaded_file.name.endswith(".csv") or uploaded_file.name.endswith(".xlsx"):
        conn = convert_to_sqlite(uploaded_file)

    @st.cache_resource(ttl="2h")
    def configure_db(_conn):
        creator = lambda: _conn
        return SQLDatabase(create_engine("sqlite:///", creator=creator))

    db = configure_db(conn)

    if uploaded_file.name.endswith(".csv") or uploaded_file.name.endswith(".xlsx"):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_conn = sqlite3.connect(tmp_db.name)
            conn.backup(tmp_conn)
            tmp_conn.close()
            st.sidebar.download_button(
                label="Download SQLite Database",
                data=Path(tmp_db.name).read_bytes(),
                file_name="converted.db"
            )

    # LLM model
    llm = ChatGroq(groq_api_key=api_key, model_name="Llama3-8b-8192", streaming=True)

    # Initialize SQLDatabaseToolkit with the SQLDatabase instance and LLM
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    # Create the SQL agent with the toolkit
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
    )

    if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    user_query = st.chat_input(placeholder="Ask anything from the database")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.chat_message("user").write(user_query)

        with st.chat_message("assistant"):
            streamlit_callback = StreamlitCallbackHandler(st.container())
            try:
                response = agent.run(user_query, callbacks=[streamlit_callback])
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.write(response)
            except Exception as e:
                st.write("Error:", e)
else:
    st.info("Please upload a SQLite, CSV, or Excel file to start querying.")