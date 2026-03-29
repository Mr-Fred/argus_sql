"""
Load golden dataset to BigQuery.
"""
import os
import logging
import json
import pandas as pd
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions
from src.scripts.data.load_datasets_to_bq import BigQueryLoader
from src.config import DATASET_CONFIG, setup_logging

logger = logging.getLogger(__name__)

def load_golden_dataset(project_id: str, dataset_id: str) -> None:
    """
    Load golden dataset to BigQuery.
    """
    with open("src/data/golden_set/golden_queries.json", "r", encoding="utf-8") as f:
        golden_dataset = json.load(f)
        dataset = pd.DataFrame(golden_dataset['golden_set'])
        try:
            loader = BigQueryLoader(project_id, dataset_id)
            loader.load_df_to_bq(dataset, "golden_set")
        except google_exceptions.GoogleAPIError as e:
            logger.exception("Error loading golden dataset to BigQuery: %s", e)

if __name__ == "__main__":
    setup_logging()
    load_dotenv()
    PROJECT_ID = os.getenv("PROJECT_ID")
    load_golden_dataset(PROJECT_ID, DATASET_CONFIG["dev"])
