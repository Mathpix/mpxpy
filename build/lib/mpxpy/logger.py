import logging
import os

logger = logging.getLogger("mathpix")


def configure_logging(level=None):
    """Configure logging for the mathpix package.

    Args:
        level: Optional logging level (e.g., logging.INFO, logging.DEBUG).
              If None, uses LOG_LEVEL environment variable or defaults to INFO.
    """
    if level is None:
        level_name = os.environ.get("MATHPIX_LOG_LEVEL", "INFO")
        level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


configure_logging()