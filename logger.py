import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'deepwell.log')

def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger('deepwell')
    logger.setLevel(logging.DEBUG)

    # rotating file handler — 5MB max, keep 5 old logs
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# global logger instance
logger = setup_logger()