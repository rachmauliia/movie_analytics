import psycopg2
import pandas as pd
from sqlalchemy import create_engine

# ── DB CONFIG ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "dvdrental",
    "user": "postgres",
    "password": "rachmaulia03",
}

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)


def get_engine():
    """Return a SQLAlchemy engine."""
    return create_engine(DATABASE_URL)


def run_query(sql: str) -> pd.DataFrame:
    """Execute a SQL query and return a DataFrame."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)