"""
Configuration for the Argus SQL project.
"""
import logging.config
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "app.log"),
            "formatter": "detailed",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "DEBUG",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

def setup_logging():
    """
    Set up logging for the application.
    """
    logging.config.dictConfig(LOGGING_CONFIG)


DATASET_CONFIG = {
    "dev": "argus_dev_dataset",
    "prod": "argus_prod_dataset"
}

LOCAL_DB_PATH = {
    "california_schools": os.path.join(BASE_DIR, "data", "raw", "california_schools.sqlite"),
    "student_club": os.path.join(BASE_DIR, "data", "raw", "student_club.sqlite")
}
