from __future__ import annotations

import pandas as pd
from sqlalchemy import (
    Column, DateTime, Float, Integer, MetaData, String, Table, create_engine, text,
)
from sqlalchemy.engine import Engine

try:
    from src.utils import CLEAN_DATA_PATH, DATABASE_PATH, get_logger
except ImportError:
    from utils import CLEAN_DATA_PATH, DATABASE_PATH, get_logger

logger = get_logger(__name__)

TABLE_NAME = "orders"
metadata = MetaData()

orders_table = Table(
    TABLE_NAME,
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("InvoiceNo", String(20), index=True),
    Column("StockCode", String(20), index=True),
    Column("Description", String(255)),
    Column("Quantity", Integer),
    Column("InvoiceDate", DateTime, index=True),
    Column("UnitPrice", Float),
    Column("CustomerID", Integer, index=True),
    Column("Country", String(100), index=True),
    Column("TotalPrice", Float),
    Column("Year", Integer),
    Column("Month", Integer),
    Column("MonthName", String(20)),
    Column("Weekday", String(20)),
)


def get_engine(connection_string: str | None = None) -> Engine:
    """
    Create (or reuse) a SQLAlchemy engine.

    Args:
        connection_string: Optional SQLAlchemy connection string. Defaults
            to a local SQLite file at database/ecommerce.db. Swap this for
            a MySQL DSN (e.g. "mysql+pymysql://user:pass@host:3306/db")
            to migrate to MySQL with no other code changes.

    Returns:
        A SQLAlchemy Engine instance.
    """
    if connection_string is None:
        connection_string = f"sqlite:///{DATABASE_PATH}"

    try:
        engine = create_engine(connection_string, echo=False, future=True)
        logger.info("Database engine created for %s", connection_string)
        return engine
    except Exception as exc:
        logger.error("Failed to create database engine: %s", exc)
        raise


def initialize_database(engine: Engine) -> None:
    """Create all tables defined in `metadata` if they don't already exist."""
    try:
        metadata.create_all(engine)
        logger.info("Database schema ensured (table '%s' ready)", TABLE_NAME)
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)
        raise


def load_dataframe_to_db(df: pd.DataFrame, engine: Engine, if_exists: str = "replace") -> None:
    """
    Write a cleaned DataFrame into the `orders` table.

    Args:
        df: Cleaned DataFrame (output of DataCleaner.clean()).
        engine: SQLAlchemy engine to write through.
        if_exists: Pandas to_sql behaviour -- 'replace' rebuilds the table
            on every run so the dashboard always reflects the latest CSV.
    """
    columns_to_store = [
        "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
        "UnitPrice", "CustomerID", "Country", "TotalPrice", "Year", "Month",
        "MonthName", "Weekday",
    ]
    try:
        subset = df[columns_to_store].copy()
        subset.to_sql(TABLE_NAME, con=engine, if_exists=if_exists, index=False)
        logger.info("Loaded %s rows into '%s' table", f"{len(subset):,}", TABLE_NAME)
    except Exception as exc:
        logger.error("Failed to load DataFrame into database: %s", exc)
        raise


def build_database_from_clean_csv(
    clean_csv_path=CLEAN_DATA_PATH, connection_string: str | None = None
) -> Engine:
    """
    End-to-end helper: read the cleaned CSV, create schema, and load data.

    Returns the engine so callers can immediately run queries against it.
    """
    engine = get_engine(connection_string)
    initialize_database(engine)

    df = pd.read_csv(
        clean_csv_path,
        parse_dates=["InvoiceDate"],
        dtype={"InvoiceNo": str, "StockCode": str},
    )
    load_dataframe_to_db(df, engine)
    return engine

# Reusable SQL query repository
class OrderQueries:
    """
    A small repository of reusable, parameterized SQL queries against the
    `orders` table. Centralizing queries here keeps raw SQL out of the
    Streamlit page code and makes each query independently testable.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def _read_sql(self, query: str, params: dict | None = None) -> pd.DataFrame:
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(text(query), conn, params=params or {})
        except Exception as exc:
            logger.error("Query failed: %s | error: %s", query[:100], exc)
            raise

    def total_revenue(self) -> float:
        query = f"SELECT COALESCE(SUM(TotalPrice), 0) AS total FROM {TABLE_NAME}"
        return float(self._read_sql(query).iloc[0]["total"])

    def total_orders(self) -> int:
        query = f"SELECT COUNT(DISTINCT InvoiceNo) AS n FROM {TABLE_NAME}"
        return int(self._read_sql(query).iloc[0]["n"])

    def total_customers(self) -> int:
        query = f"SELECT COUNT(DISTINCT CustomerID) AS n FROM {TABLE_NAME}"
        return int(self._read_sql(query).iloc[0]["n"])

    def total_products(self) -> int:
        query = f"SELECT COUNT(DISTINCT StockCode) AS n FROM {TABLE_NAME}"
        return int(self._read_sql(query).iloc[0]["n"])

    def revenue_by_month(self) -> pd.DataFrame:
        query = f"""
            SELECT MonthName, Year, Month, SUM(TotalPrice) AS Revenue
            FROM {TABLE_NAME}
            GROUP BY Year, Month, MonthName
            ORDER BY Year, Month
        """
        return self._read_sql(query)

    def revenue_by_country(self, top_n: int = 10) -> pd.DataFrame:
        query = f"""
            SELECT Country, SUM(TotalPrice) AS Revenue, COUNT(DISTINCT InvoiceNo) AS Orders
            FROM {TABLE_NAME}
            GROUP BY Country
            ORDER BY Revenue DESC
            LIMIT :top_n
        """
        return self._read_sql(query, {"top_n": top_n})

    def top_customers(self, top_n: int = 10) -> pd.DataFrame:
        query = f"""
            SELECT CustomerID, SUM(TotalPrice) AS Revenue, COUNT(DISTINCT InvoiceNo) AS Orders
            FROM {TABLE_NAME}
            GROUP BY CustomerID
            ORDER BY Revenue DESC
            LIMIT :top_n
        """
        return self._read_sql(query, {"top_n": top_n})

    def top_products(self, top_n: int = 10) -> pd.DataFrame:
        query = f"""
            SELECT Description, StockCode, SUM(TotalPrice) AS Revenue, SUM(Quantity) AS QuantitySold
            FROM {TABLE_NAME}
            GROUP BY StockCode, Description
            ORDER BY Revenue DESC
            LIMIT :top_n
        """
        return self._read_sql(query, {"top_n": top_n})
