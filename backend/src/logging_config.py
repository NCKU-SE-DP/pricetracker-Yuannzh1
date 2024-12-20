import logging
from logging.handlers import RotatingFileHandler
import sentry_sdk
from src.config import DSN, LOG_FORMAT, LOG_FILE
# 初始化 Sentry

sentry_sdk.init(
        dsn=DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

def setup_logger():
    logger = logging.getLogger("PriceTrackerLogger")
    logger.setLevel(logging.DEBUG)

    # StreamHandler - 輸出到螢幕
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # RotatingFileHandler - 輸出到檔案，並支援輪替
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # 確保不重複添加 handler
    if not logger.hasHandlers():
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()