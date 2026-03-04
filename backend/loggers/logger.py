import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = "C:/Users/SkandaSankarRaman/OneDrive - GapBlue Software Labs Pvt Ltd/Work/SpeechDiarization/backend/loggers/time_logs.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


def configure_logger():
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger()  # top-level app logger

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | [%(levelname)s] | %(filename)s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = False

    return logger
