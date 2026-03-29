"""
Load datasets to BigQuery.
"""
import os
import logging
import re
from dotenv import load_dotenv
from google.cloud import bigquery
from google.api_core import exceptions as google_exceptions
import pandas as pd
from src.config import DATASET_CONFIG, LOCAL_DB_PATH, setup_logging
from src.scripts.data.sqlite_extractor import SQLiteExtractor

logger = logging.getLogger(__name__)

class BigQueryLoader:
    """
    Load datasets to BigQuery.
    """
    def __init__(self, project_id: str, dataset_id: str):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)

    def create_dataset(self) -> None:
        """
        Create a dataset in BigQuery.
        """
        try:
            dataset_ref = self.client.dataset(self.dataset_id)
            dataset = bigquery.Dataset(dataset_ref)
            self.client.create_dataset(dataset, exists_ok=True)
            logger.info("Created dataset %s.%s", self.project_id, self.dataset_id)
        except google_exceptions.GoogleAPIError as e:
            logger.exception("Error creating dataset: %s", e)

    def load_df_to_bq(self, df: pd.DataFrame, table_id: str) -> None:
        """
        Load a DataFrame to BigQuery.
        """
        # Clean column names to be valid BigQuery identifiers
        # Replace spaces with underscores and remove special characters
        df.columns = [re.sub(r'[^A-Za-z0-9_]+', '_', col) for col in df.columns]

        try:
            table_ref = self.client.dataset(self.dataset_id).table(table_id)
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE",
            )
            job = self.client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()  # Wait for the job to complete
            table = self.client.get_table(table_ref)
            logger.info(
                "Loaded %s rows to BigQuery table %s.%s.%s",
                table.num_rows,
                self.project_id,
                self.dataset_id,
                table_id
            )
        except google_exceptions.GoogleAPIError as e:
            logger.exception("Error loading table %s to BigQuery: %s", table_id, e)

    def load_datasets(self) -> None:
        """
        Load all datasets to BigQuery.
        """
        self.create_dataset()
        for dataset_path in LOCAL_DB_PATH.values():
            with SQLiteExtractor(dataset_path) as extractor:
                for table_name, table_df in extractor.stream_dataframes():
                    self.load_df_to_bq(table_df, table_name)


if __name__ == "__main__":
    setup_logging()
    load_dotenv()
    PROJECT_ID = os.getenv("PROJECT_ID")
    loader = BigQueryLoader(PROJECT_ID, DATASET_CONFIG["dev"])
    loader.load_datasets()
