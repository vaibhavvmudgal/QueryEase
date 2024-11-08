from dotenv import load_dotenv
import streamlit as st
import os
import sqlite3
import pandas as pd
import google.generativeai as genai

# Load environment variables (including the API key if set in .env)
load_dotenv()

# Default API key for Generative AI (Gemini) if not set in environment variables
default_api_key = "AIzaSyA-LVGYTO-tHAx2wsUOolsQhNcSSmWyNfo"
genai.configure(api_key=os.getenv("GOOGLE_API_KEY", default_api_key))

# Function to load the Google Gemini model and get a response to the query
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], question])
    return response.text

# Function to retrieve a query result from the database
def read_sql_query(sql, db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

# Define the prompt
prompt = [
    """
    You are an expert in converting English questions to SQL queries!
    The SQL database has the name 'STUDENT' and has the following columns: NAME, CLASS, and SECTION.
    
    For example:
    - Example 1: "How many entries of records are present?" -> SELECT COUNT(*) FROM STUDENT;
    - Example 2: "Tell me all the students studying in Data Science class?" -> SELECT * FROM STUDENT WHERE CLASS="Data Science";
    
    Please avoid using "```" and "sql" in your output.
    """
]

# Streamlit App Setup
st.set_page_config(page_title="QueryEase - Gemini SQL Query", page_icon="✨")
st.header("Gemini App to Retrieve SQL Data")

# File upload
uploaded_file = st.file_uploader("Upload a CSV, Excel, or SQLite file", type=["csv", "xlsx", "db", "sqlite"])

# Convert uploaded file to SQLite database
def convert_to_sqlite(file):
    conn = sqlite3.connect(":memory:")  # Temporary in-memory SQLite database
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
        df.to_sql("STUDENT", conn, index=False, if_exists="replace")
    elif file.name.endswith(".xlsx"):
        df = pd.read_excel(file)
        df.to_sql("STUDENT", conn, index=False, if_exists="replace")
    elif file.name.endswith(".db") or file.name.endswith(".sqlite"):
        conn = sqlite3.connect(file)  # Use the SQLite file directly
    return conn

# Initialize database connection if file is uploaded
if uploaded_file is not None:
    conn = convert_to_sqlite(uploaded_file)
    db_path = ":memory:"  # Use in-memory path for querying

    # Take user input for question
    question = st.text_input("Input your query:", key="input")
    submit = st.button("Ask the question")

    # If submit button is clicked, proceed
    if submit:
        # Generate SQL query from question using Gemini
        sql_query = get_gemini_response(question, prompt).strip()
        st.write("Generated SQL Query:", sql_query)

        # Execute the query and display results
        try:
            response = read_sql_query(sql_query, db_path)
            st.subheader("The Response is:")
            for row in response:
                st.write(row)
        except Exception as e:
            st.error(f"Error executing SQL query: {e}")
else:
    st.info("Please upload a CSV, Excel, or SQLite file to start querying.")
