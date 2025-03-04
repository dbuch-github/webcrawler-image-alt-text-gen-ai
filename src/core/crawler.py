"""
Main web crawler implementation that ties together all services
"""
import time
import logging
from typing import Dict, List, Any, Optional, Union

from .models import Image, Headline, WebPage
from .services.page_loader import PageLoaderService
from .services.content_extractor import ContentExtractorService
from .services.image_extractor import ImageExtractorService
from .services.screenshot_service import ScreenshotService
from ..infrastructure.webdriver_factory import WebDriverFactory

logger = logging.getLogger(__name__)

class WebCrawler:
    """
    Main crawler class that coordinates the extraction of content from web pages
    """
    
    def __init__(self, headless: bool = True, timeout: int = 20, browser: str = 'auto'):
        """
        Initialize the web crawler
        
        Args:
            headless (bool): Run browser in headless mode if True
            timeout (int): Wait timeout in seconds
            browser (str): Browser to use ('chrome', 'firefox', or 'auto')
        """
        self.timeout = timeout
        self.browser_type = browser
        
        # Create WebDriver
        self.driver = WebDriverFactory.create_driver(browser_type=browser, headless=headless)
        
        # Initialize services
        self.page_loader = PageLoaderService(self.driver, timeout)
        self.content_extractor = ContentExtractorService(self.driver)
        self.image_extractor = ImageExtractorService(self.driver)
        self.screenshot_service = ScreenshotService(self.driver)
    
    def __del__(self):
        """Clean up by closing the browser when the instance is destroyed"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass
    
    def load_page(self, url: str) -> bool:
        """
        Load a webpage and handle cookies/consent forms
        
        Args:
            url (str): The URL to load
            
        Returns:
            bool: True if page loaded successfully, False otherwise
        """
        return self.page_loader.load_page(url)
    
    def get_page_title(self) -> str:
        """
        Extract the page title
        
        Returns:
            str: Page title
        """
        return self.content_extractor.get_page_title()
    
    def get_headlines(self) -> Dict[str, List[Union[Dict[str, Any], Headline]]]:
        """
        Extract all h1, h2, and h3 headlines from the page
        
        Returns:
            dict: Dictionary with headline tags as keys and lists of headline info as values
        """
        headline_dict = self.content_extractor.get_headlines()
        
        # Convert to dict format for backward compatibility
        return {
            tag: [headline.to_dict() for headline in headlines]
            for tag, headlines in headline_dict.items()
        }
    
    def get_text_content(self) -> str:
        """
        Extract the main text content from the page
        
        Returns:
            str: Main text content
        """
        return self.content_extractor.get_text_content()
    
    def get_images(self) -> List[Dict[str, Any]]:
        """
        Extract all images from the page using multiple methods
        
        Returns:
            list: List of dictionaries with image information
        """
        images = self.image_extractor.get_images()
        
        # Convert to dict format for backward compatibility
        return [image if isinstance(image, dict) else image.to_dict() for image in images]
    
    def get_images_from_iframes(self) -> List[Dict[str, Any]]:
        """
        Extract images from all iframes on the page
        
        Returns:
            list: List of dictionaries with image information from iframes
        """
        images = self.image_extractor.get_images_from_iframes()
        
        # Convert to dict format for backward compatibility
        return [image if isinstance(image, dict) else image.to_dict() for image in images]
    
    def scroll_page(self) -> bool:
        """
        Basic page scrolling to trigger lazy-loaded content
        
        Returns:
            bool: True if scrolling completed successfully
        """
        try:
            # Get the page height
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll in increments
            for i in range(0, page_height, 300):
                self.driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.1)  # Short delay to allow content to load
                
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            return True
        except Exception as e:
            logger.error(f"Error scrolling page: {str(e)}")
            return False
    
    def take_screenshot(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        Take a screenshot of the current page
        
        Args:
            output_path (str, optional): Path to save the screenshot. If None, a temporary file is created.
            
        Returns:
            str: Path to the screenshot file, or None if there was an error
        """
        return self.screenshot_service.take_screenshot(output_path)
    
    # Expose internal methods for backward compatibility
    
    def _handle_consent_banners(self) -> bool:
        """
        Identify and accept common consent banners and cookie notices
        
        Returns:
            bool: True if clicked on a consent button, False otherwise
        """
        return self.page_loader.handle_consent_banners()
    
    def _scroll_for_lazy_content(self) -> None:
        """
        Enhanced scrolling to trigger lazy loading of images and other content
        """
        self.page_loader.scroll_for_lazy_content()
    
    def _wait_for_network_idle(self, timeout=10, max_connections=0, wait_time=1.0) -> bool:
        """
        Wait for network to be idle (no active connections)
        
        Args:
            timeout (int): Maximum time to wait in seconds
            max_connections (int): Maximum number of active connections to consider as 'idle'
            wait_time (float): Time to wait after network becomes idle
            
        Returns:
            bool: True if network became idle, False if timed out
        """
        return self.page_loader.wait_for_network_idle(timeout, max_connections, wait_time)


# Convenience functions for backward compatibility

def scrape_url(url: str, headless: bool = True, browser: str = 'auto') -> Dict[str, Any]:
    """
    Scrape a URL and return all extracted data
    
    Args:
        url (str): URL to scrape
        headless (bool): Run in headless mode if True
        browser (str): Browser to use ('chrome', 'firefox', or 'auto')
        
    Returns:
        dict: Dictionary containing all scraped data
    """
    crawler = WebCrawler(headless=headless, browser=browser)
    success = crawler.load_page(url)
    
    if not success:
        return {'error': f'Failed to load {url}'}
    
    result = {
        'url': url,
        'title': crawler.get_page_title(),
        'headlines': crawler.get_headlines(),
        'text_content': crawler.get_text_content(),
        'images': crawler.get_images()
    }
    
    return result

def get_page_title(url: str, headless: bool = True, browser: str = 'auto') -> str:
    """
    Extract only the page title from a URL
    
    Args:
        url (str): URL to scrape
        headless (bool): Run in headless mode if True
        browser (str): Browser to use ('chrome', 'firefox', or 'auto')
    """
    crawler = WebCrawler(headless=headless, browser=browser)
    success = crawler.load_page(url)
    
    if not success:
        return f'Failed to load {url}'
    
    return crawler.get_page_title()

def get_headlines(url: str, headless: bool = True, browser: str = 'auto') -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract only the headlines from a URL
    
    Args:
        url (str): URL to scrape
        headless (bool): Run in headless mode if True
        browser (str): Browser to use ('chrome', 'firefox', or 'auto')
    """
    crawler = WebCrawler(headless=headless, browser=browser)
    success = crawler.load_page(url)
    
    if not success:
        return {'error': f'Failed to load {url}'}
    
    return crawler.get_headlines()

def get_text_content(url: str, headless: bool = True, browser: str = 'auto') -> str:
    """
    Extract only the text content from a URL
    
    Args:
        url (str): URL to scrape
        headless (bool): Run in headless mode if True
        browser (str): Browser to use ('chrome', 'firefox', or 'auto')
    """
    crawler = WebCrawler(headless=headless, browser=browser)
    success = crawler.load_page(url)
    
    if not success:
        return f'Failed to load {url}'
    
    return crawler.get_text_content()

def get_images(url: str, headless: bool = True, browser: str = 'auto') -> Union[Dict[str, str], List[Dict[str, Any]]]:
    """
    Extract only the images from a URL
    
    Args:
        url (str): URL to scrape
        headless (bool): Run in headless mode if True
        browser (str): Browser to use ('chrome', 'firefox', or 'auto')
    """
    crawler = WebCrawler(headless=headless, browser=browser)
    success = crawler.load_page(url)
    
    if not success:
        return {'error': f'Failed to load {url}'}
    
    # Scroll the page to trigger lazy-loaded images
    crawler.scroll_page()
    
    # Get images from main page
    images = crawler.get_images()
    
    # Also get images from iframes
    iframe_images = crawler.get_images_from_iframes()
    if iframe_images:
        images.extend(iframe_images)
    
    return images