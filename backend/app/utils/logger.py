import logging
import sys

def setup_logger(name: str = "exam_slayer") -> logging.Logger:
    """Configures and returns a logger instance with standardized formatting."""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Create console handler with format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Disable propagation to prevent root logger duplication
    logger.propagate = False
    
    return logger

# Shared logger instance
logger = setup_logger()
