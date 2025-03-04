"""
Application configuration module
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class CrawlerConfig:
    """
    Configuration for the WebCrawler
    """
    headless: bool = True
    timeout: int = 20
    browser: str = 'auto'
    consent_delay: int = 2
    check_iframes: bool = True
    detect_cdn: bool = True
    enhanced_scrolling: bool = True
    check_shadow_dom: bool = True
    min_wait_time: int = 3
    screenshot_resolution: tuple = (1920, 1080)
    
@dataclass
class AppConfig:
    """
    Application-wide configuration
    """
    crawler: CrawlerConfig = CrawlerConfig()
    temp_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'temp')
    debug: bool = False
    
    def __post_init__(self):
        """Create temp directory if it doesn't exist"""
        os.makedirs(self.temp_dir, exist_ok=True)

# Create default configuration instance
config = AppConfig()