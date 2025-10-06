import logging
import sys
from pathlib import Path

def get_logger(name: str = None) -> logging.Logger:
    # Derive name automatically from the file that called the function if name is not provided
    if name is None:
        # get name of the file that imported the logger
        caller = Path(sys._getframe(1).f_code.co_filename).stem
        name = caller

    # Create or get logger
    logger = logging.getLogger(name)

    # Prevent duplicate handlers if called multiple times
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        
        handler = logging.StreamHandler(sys.stdout)

        
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] → %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        # Attach handler
        logger.addHandler(handler)

    return logger
