import logging
import sys

def setup_logging():
    """
    Configures logging to output to both console and a file ('app.log').
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Prevent adding handlers multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a file handler
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Create a stream handler (for console output)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger

# Initialize and export the logger
logger = setup_logging()
