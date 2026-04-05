"""
BigQuery client module for interacting with BigQuery.

This module provides functionality to create and update tables
and extract data and metadata in BigQuery
using SQL queries.
"""
import logging
from typing import Any, Dict, List
from google.cloud import bigquery
from src.config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()

# TODO: Implement the Pydantic Entity Models and Transformation layer

# 1. Decide on sampling based on table size. 10GB threshold for enterprise-scale sampling.
LARGE_TABLE_BYTES = 10 * 1024**3
LARGE_TABLE_ROWS = 1_000_000


class BigQueryClient:
    """Extractor for BigQuery schema information."""

    def __init__(self, project_id: str, dataset_id: str):
        """
        Initialize the BigQuery extractor.

        Args:
            project_id: The Google Cloud project ID.
            dataset_id: The BigQuery dataset ID.
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)

    def execute_query(self, query: str, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.

        Args:
            query: The SQL query to execute.
            dry_run: Whether to perform a dry run of the query.
        Returns:
            A list of dictionaries containing the query results.
        """
        try:
            if dry_run:
                operation = bigquery.QueryJobConfig(dry_run=True)
                query_job = self.client.query(query, job_config=operation)
                return query_job.total_bytes_processed
            query_job = self.client.query(query)
            results = [dict(row) for row in query_job.result()]
            logger.info(
                "Executed query successfully and returned %d rows", len(results)
            )
            return results
        except Exception as e:
            logger.exception("Error executing query: %s", e)
            raise

    def list_tables(self) -> List[str]:
        """
        List all tables in the dataset.

        Returns:
            A list of table IDs.
        """
        try:
            tables = self.client.list_tables(f"{self.project_id}.{self.dataset_id}")
            return tables
        except Exception as e:
            logger.exception("Error listing tables: %s", e)
            raise

    def create_table(self, table_id: str, schema: List[Dict[str, Any]]) -> None:
        """
        Create a table in BigQuery.

        Args:
            table_id: The ID of the table to create.
            schema: A list of dictionaries containing schema information.
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_id}"
            table = bigquery.Table(table_ref, schema=schema)
            self.client.create_table(table)
            logger.info("Table %s created successfully", table_id)
        except Exception as e:
            logger.exception("Error creating table: %s", e)
            raise

    def update_table(self, table_id: str, schema: List[Dict[str, Any]]) -> None:
        """
        Update a table in BigQuery.

        Args:
            table_id: The ID of the table to update.
            schema: A list of dictionaries containing schema information.
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_id}"
            table = bigquery.Table(table_ref, schema=schema)
            self.client.update_table(table, ["schema"])
            logger.info("Table %s updated successfully", table_id)
        except Exception as e:
            logger.exception("Error updating table: %s", e)
            raise

    def extract_information_schema(self, table_id: str = None) -> List[Dict[str, Any]]:
        """
        Extract the information schema of a table in BigQuery.

        Args:
            table_id: The ID of the table to extract the schema from.
        Returns:
            A list of dictionaries containing the schema information.
        """
        query = f"""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    description
                FROM {self.project_id}.{self.dataset_id}.INFORMATION_SCHEMA.COLUMNS
                """
        try:
            if table_id:
                query += f"WHERE table_name = '{table_id}'"
                logger.info("Extracting physical schema from table: %s", table_id)
                logger.info("Query: %s", query)
                return self.execute_query(query)
            else:
                logger.info("Extracting physical schema from all tables")
                logger.info("Query: %s", query)
                return self.execute_query(query)
        except Exception as e:
            logger.exception("Error extracting table: %s", e)
            raise

    def extract_statistical_metadata(
        self, table: bigquery.Table, dry_run: bool
    ) -> List[Dict[str, Any]]:
        """
        Extract the statistical information of a table in BigQuery.

        Args:
            table_id: The ID of the table to extract the metadata from.
        Returns:
            A list of dictionaries containing the statistical information.
        """

        query = ""
        # If table is larger than 10GB or 1M rows, use sampling
        sampling_clause = ""
        if (
            table.num_bytes > LARGE_TABLE_BYTES
            or table.num_rows > LARGE_TABLE_ROWS
        ):
            # STREATEGY: TABLESAMPLE SYSTEM
            # This is a BigQuery-specific syntax that allows you to sample a table.
            # Only scans a fraction of the data blocks.
            # NOTE: We use 1% or 10% depending on the size of the table
            # to ensure we get *some* data.
            percent = 1 if table.num_bytes > (10 * LARGE_TABLE_BYTES) else 10
            sampling_clause = f"TABLESAMPLE SYSTEM ({percent} PERCENT)"
        else:
            # STRATEGY: APPROX_TOP_COUNT (Full Scan - Low Cost)
            # Why: For small tables (<1GB), a full column scan is cheap (0.005 per GB).
            # This is better for Schema linking
            # because it finds the 'most popular" values rather than random rare ones.
            sampling_clause = ""

        # 2. Build the dynamic query for column-level stats based on its type
        select_parts = []
        for col in table.schema:
            col_name = f"`{col.name}`"

            # String/Categorical: Get top 10 values for Schema linking
            if col.field_type in ["STRING", "GEOGRAPHY"]:
                select_parts.append(
                    f"APPROX_TOP_COUNT({col_name}, 10) as `{col.name}_top_values`"
                )
                select_parts.append(
                    f"COUNTIF({col_name} IS NOT NULL) as `{col.name}_non_null_count`"
                )
            # Numeric: Get quartiles and mean
            elif col.field_type in [
                "INTEGER",
                "FLOAT",
                "NUMERIC",
                "BIGNUMERIC",
                "DATE",
                "DATETIME",
                "TIMESTAMP",
            ]:
                select_parts.append(f"MIN({col_name}) as `{col.name}_min`")
                select_parts.append(f"MAX({col_name}) as `{col.name}_max`")
            # Array: Get count of non-null values
            elif col.field_type in ["ARRAY", "STRUCT"]:
                select_parts.append(
                    f"COUNTIF({col_name} IS NOT NULL) as `{col.name}_non_null_count`"
                )
        if not select_parts:
            return []

        # 3. Execute all queries in parallel
        query = f"""
        SELECT 
            {', '.join(select_parts)}
        FROM `{self.project_id}.{self.dataset_id}.{table.table_id}`
        {sampling_clause}
        """
        try:
            return self.execute_query(query, dry_run=dry_run)
        except Exception as e:
            logger.exception("Error extracting table: %s", e)
            raise
    
    def get_table_by_name(self, table_id: str) -> bigquery.Table:
        """
        Get a table by name.

        Args:
            table_id: The ID of the table to get.
        Returns:
            A bigquery.Table object.
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_id}"
            table = self.client.get_table(table_ref)
            return table
        except Exception as e:
            logger.exception("Error getting table: %s", e)
            raise

    def upsert_m_schema(self, table_id: str, m_schema_json: Dict[str, Any]) -> None:
        """
        Upserts the final augmented M-Schema into the metadata table and triggers
        native BigQuery ML.GENERATE_EMBEDDING generation.
        """
        # TODO: Implement the SQL MERGE statement with native embeddings
        pass