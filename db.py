import psycopg2
from sqlalchemy import create_engine
import streamlit as st

def get_sqlalchemy_engine():
    """Returns a SQLAlchemy engine for connecting to the Ramdan PostgreSQL branch."""
    
    branch = "ramdan"  # Force connection to Ramdan branch

    # Load database host from secrets
    db_host = st.secrets["database"]["hosts"].get(branch, st.secrets["database"]["hosts"]["ramdan"])
    db_user = st.secrets["database"]["user"]
    db_password = st.secrets["branch_passwords"].get(branch, st.secrets["branch_passwords"]["ramdan"])
    db_name = st.secrets["database"]["database"]  # Same database name, different branches

    # ✅ Construct the database URL dynamically
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"

    return create_engine(db_url, pool_pre_ping=True)

def get_db_connection():
    """Establish and return a database connection to the Ramdan branch."""
    try:
        branch = "ramdan"  # Force connection to Ramdan branch

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
    """Return only the Ramdan branch."""
    return ["ramdan"]  # Hardcoded to return only "ramdan"
