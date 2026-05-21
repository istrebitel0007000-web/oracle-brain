import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """
    Emit one JSON object per log record.
    Enable via LOG_FORMAT=json environment variable.
    """
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
