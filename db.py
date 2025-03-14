import psycopg2
from sqlalchemy import create_engine
import streamlit as st

from sqlalchemy import create_engine
import streamlit as st

def get_sqlalchemy_engine(branch=None):
    """Get SQLAlchemy engine for the specified branch"""
    db_url_template = "postgresql+psycopg2://{user}:{password}@{host}/{database}"
    
    # Fetch credentials from Streamlit secrets
    db_credentials = st.secrets["database"]
    
    # Construct the DB URL with the branch name as the database
    db_url = db_url_template.format(
        user=db_credentials["user"],
        password=db_credentials["password"],
        host=db_credentials["host"],
        database=branch if branch else db_credentials["database"],  # Use branch as database
    )
    
    return create_engine(db_url)

def get_db_connection():
    """Establish and return a database connection based on the user's assigned branch."""
    try:
        branch = st.session_state.get("branch", "main")  # Default to 'main'

        db_host = st.secrets["database"]["hosts"].get(branch)
        db_password = st.secrets["branch_passwords"].get(branch)
        db_user = st.secrets["database"]["user"]
        db_name = st.secrets["database"]["database"]

        if not db_host or not db_password:
            raise ValueError(f"❌ Invalid database host or missing password for branch: {branch}")

        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=5432
        )
        return conn

    except Exception as e:
        print(f"❌ Database connection failed: {e}")  # ✅ Log error instead of using `st.error()`
        return None  # Return None to be handled by the caller

def get_branches():
    """Fetch available branches from the database."""
    conn = get_db_connection()
    if not conn:
        return ["main"]  # Fallback to 'main' if DB connection fails

    try:
        cur = conn.cursor()
        cur.execute("SELECT branch_name FROM public.branches")  # Explicit schema
        branches = [row[0] for row in cur.fetchall()]
        return branches  # ✅ Return fetched branches
    except Exception as e:
        print(f"❌ Failed to fetch branches: {e}")  # ✅ Log error instead of `st.error()`
        return ["main"]
    finally:
        if conn:
            conn.close()  # ✅ Ensure connection is always closed
