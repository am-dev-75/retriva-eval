import logging
import sys
from retriva_eval.logger.config import logger_settings

def setup_logging():
    """
    Configures the project-wide logging parameters based on settings.
    This should be called as early as possible in the application's entry point.
    """
    log_level_name = logger_settings.log_level.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y%m%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with the given name.
    """
    return logging.getLogger(name)
