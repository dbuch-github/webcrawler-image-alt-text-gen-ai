"""
Infrastructure layer for the webcrawler application.

This package contains code that interacts with external services, 
libraries, and systems that are not part of the core business logic.
"""

from .config import config, AppConfig, CrawlerConfig
from .logging_config import configure_logging
from .webdriver_factory import WebDriverFactory

# Configure application logging
logger = configure_logging()

__all__ = [
    'config', 'AppConfig', 'CrawlerConfig', 
    'configure_logging', 'WebDriverFactory',
    'logger'
]