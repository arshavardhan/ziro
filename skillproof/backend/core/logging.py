import logging
from core.guardrails import redact

class RedactedFormatter(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))

def configure():
    logger = logging.getLogger('skillproof')
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(RedactedFormatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = configure()
