"""
Logging configuration for the application
"""
import logging
import sys

def configure_logging(level=logging.INFO):
    """
    Configure application-wide logging.
    
    Args:
        level (int): Logging level (e.g., logging.INFO, logging.DEBUG)
    """
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create logger for our app
    app_logger = logging.getLogger('webcrawler')
    app_logger.setLevel(level)
    
    return app_logger