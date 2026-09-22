"""Database Gateway and Schema Manager for StockLane.
Supports:
  1. PostgreSQL (production relational schema, staging, core, analytics)
  2. DuckDB (embedded PostgreSQL-compatible analytical engine for seamless local execution)
Manages table creation, data loading, and analytical SQL views.
"""
import os
from pathlib import Path
from typing import Dict, Any
import duckdb
import pandas as pd
from python.common.logger import setup_logger

logger = setup_logger("DatabaseManager")

class DatabaseManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backend = config.get("database", {}).get("backend", "duckdb")
        self.duckdb_path = config.get("database", {}).get("duckdb_path", "data/stocklane.duckdb")
        self.conn = None
        
    def get_connection(self):
        if self.conn is None:
            if self.backend == "duckdb":
                db_file = Path(self.duckdb_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)
                self.conn = duckdb.connect(str(db_file))
            elif self.backend == "postgres":
                import psycopg
                pg_cfg = self.config["database"]
                self.conn = psycopg.connect(
                    host=pg_cfg.get("postgres_host", "localhost"),
                    port=pg_cfg.get("postgres_port", 5432),
                    user=pg_cfg.get("postgres_user", "postgres"),
                    password=pg_cfg.get("postgres_password", ""),
                    dbname=pg_cfg.get("postgres_db", "stocklane")
                )
        return self.conn
        
    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            
    def initialize_schema(self):
        """Creates schemas and tables."""
        conn = self.get_connection()
        if self.backend == "duckdb":
            conn.execute("CREATE SCHEMA IF NOT EXISTS staging;")
            conn.execute("CREATE SCHEMA IF NOT EXISTS core;")
            conn.execute("CREATE SCHEMA IF NOT EXISTS analytics;")
            logger.info("DuckDB schemas (staging, core, analytics) initialized.")
            
    def load_table(self, schema: str, table_name: str, df: pd.DataFrame):
        """Registers and replaces table in schema with pandas dataframe."""
        conn = self.get_connection()
        full_table = f"{schema}.{table_name}"
        if self.backend == "duckdb":
            # Direct high speed zero-copy ingestion
            conn.register("temp_df", df)
            conn.execute(f"CREATE OR REPLACE TABLE {full_table} AS SELECT * FROM temp_df;")
            conn.unregister("temp_df")
            logger.info(f"Loaded {len(df):,} rows into {full_table}.")
            
    def execute_sql(self, sql_statement: str):
        conn = self.get_connection()
        return conn.execute(sql_statement)
        
    def query(self, sql_query: str) -> pd.DataFrame:
        conn = self.get_connection()
        return conn.execute(sql_query).df()
