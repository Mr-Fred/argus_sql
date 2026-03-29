"""
Connect to SQLite database and extract data.
"""
import logging
from typing import Iterator
import sqlite3
import pandas as pd

logger = logging.getLogger(__name__)

class SQLiteExtractor:
    """
    Extract data from SQLite database.
    """
    def __init__(self, database: str):
        self.database = database
        self.conn = None

    def __enter__(self):
        # Setup: Open the connection
        logger.info("Connecting to database: %s", self.database)
        try:
            self.conn = sqlite3.connect(self.database)
            return self
        except sqlite3.Error as e:
            logger.exception("Error connecting to database: %s", e)
            raise

    def list_tables(self) -> list[str]:
        """
        Get all tables in the database.
        """
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
        except sqlite3.Error as e:
            logger.exception("Error listing tables: %s", e)
        return [t[0] for t in tables]

    def get_table_schema(self, table_name: str) -> list[str]:
        """
        Get the schema of a table.
        """
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                schema = cursor.fetchall()
        except sqlite3.Error as e:
            logger.exception("Error getting table schema: %s", e)
        return schema

    def extract_table_to_df(self, table_name: str) -> pd.DataFrame:
        """
        Extract a table to a pandas DataFrame.
        """
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
            return df
        except sqlite3.Error as e:
            logger.exception("Error extracting table: %s", e)

    def stream_dataframes(self) -> Iterator[tuple[str, pd.DataFrame]]:
        """
        Stream all tables in the database to pandas DataFrames.
        """
        tables = self.list_tables()
        for table in tables:
            yield (table, self.extract_table_to_df(table))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed safely.")
        if exc_type:
            # exc_info=True automatically attaches the stack trace to the log
            logger.exception("Transaction failed: %s", exc_val)
            return False

if __name__ == "__main__":
    with SQLiteExtractor("../../data/raw/student_club.sqlite") as extractor:
        for tbl_name, tbl_df in extractor.stream_dataframes():
            print(tbl_name, tbl_df.head())
            break
