import logging
import os
from pythonjsonlogger import jsonlogger

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def configure_logging():
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Avoid duplicate handlers in reload environments
    if root.handlers:
        return

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(trace_id)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
