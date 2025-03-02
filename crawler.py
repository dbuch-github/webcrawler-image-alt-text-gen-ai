import time
import platform
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self, headless=True, timeout=20, browser='auto'):
        """
        Initialize the web crawler with Selenium WebDriver
        
        Args:
            headless (bool): Run browser in headless mode if True
            timeout (int): Wait timeout in seconds
            browser (str): Browser to use ('chrome', 'firefox', or 'auto')
        """
        self.timeout = timeout
        self.browser_type = browser
        
        # Detect system architecture
        self.system = platform.system().lower()
        self.is_arm = platform.machine().lower() in ('arm', 'arm64', 'aarch64')
        
        # Try to initialize with the selected browser or fallback to available ones
        if self.browser_type == 'auto' or self.browser_type == 'chrome':
            try:
                self._setup_chrome(headless)
            except WebDriverException as e:
                logger.warning(f"Failed to initialize Chrome: {str(e)}")
                if self.browser_type == 'auto':
                    logger.info("Trying Firefox instead")
                    self._setup_firefox(headless)
                else:
                    raise
        elif self.browser_type == 'firefox':
            self._setup_firefox(headless)
        else:
            raise ValueError(f"Unsupported browser type: {self.browser_type}")
        
    def _setup_chrome(self, headless):
        """Setup Chrome WebDriver"""
        options = ChromeOptions()
        
        # Set user agent to mimic a normal browser
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        if headless:
            options.add_argument("--headless=new")
        
        # Additional options to make the crawler more robust
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        
        # Handle ARM architectures specifically
        if self.is_arm and self.system == 'darwin':
            logger.info("Detected macOS ARM architecture")
            chrome_version = ChromeDriverManager().driver.get_latest_release_version()
            options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            # Initialize the WebDriver
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager(driver_version=chrome_version).install()),
                options=options
            )
        else:
            # Standard initialization
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options
            )
        
        logger.info("Chrome WebDriver initialized successfully")
            
    def _setup_firefox(self, headless):
        """Setup Firefox WebDriver"""
        options = FirefoxOptions()
        
        # Set user agent
        options.set_preference("general.useragent.override", 
                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0")
        
        if headless:
            options.add_argument("--headless")
        
        # Additional options
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("app.update.auto", False)
        
        # Initialize the WebDriver
        self.driver = webdriver.Firefox(
            service=FirefoxService(GeckoDriverManager().install()),
            options=options
        )
        
        logger.info("Firefox WebDriver initialized successfully")
        
    def __del__(self):
        """Clean up by closing the browser when the instance is destroyed"""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def load_page(self, url):
        """
        Load a webpage and handle cookies/consent forms
        
        Args:
            url (str): The URL to load
            
        Returns:
            bool: True if page loaded successfully, False otherwise
        """
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle cookie consent forms and banners
            self._handle_consent_banners()
            
            return True
        
        except TimeoutException:
            print(f"Timeout while loading {url}")
            return False
        except Exception as e:
            print(f"Error loading {url}: {str(e)}")
            return False
    
    def _handle_consent_banners(self):
        """
        Identify and accept common consent banners and cookie notices
        """
        # List of common consent button identifiers
        consent_identifiers = [
            # Common class names
            ".//button[contains(@class, 'consent') or contains(@class, 'cookie') or contains(@class, 'accept') or contains(@class, 'agree')]",
            ".//a[contains(@class, 'consent') or contains(@class, 'cookie') or contains(@class, 'accept') or contains(@class, 'agree')]",
            
            # Common ID patterns
            ".//*[contains(@id, 'consent') or contains(@id, 'cookie') or contains(@id, 'accept') or contains(@id, 'agree')]",
            
            # Common text in buttons
            ".//button[contains(text(), 'Accept') or contains(text(), 'Agree') or contains(text(), 'OK') or contains(text(), 'Got it')]",
            ".//button[contains(text(), 'accept cookies') or contains(text(), 'accept all') or contains(text(), 'allow cookies')]",
            
            # Common GDPR/cookie specific buttons (case insensitive)
            ".//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all cookies')]",
            ".//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept necessary cookies')]",
            
            # German consent buttons
            ".//button[contains(text(), 'Akzeptieren') or contains(text(), 'Zustimmen') or contains(text(), 'Einverstanden')]",
            
            # French consent buttons
            ".//button[contains(text(), 'Accepter') or contains(text(), 'J'accepte')]",
        ]
        
        # Try each identifier
        for xpath in consent_identifiers:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        time.sleep(1)  # Wait for banner to disappear
                        return
            except (NoSuchElementException, Exception):
                continue
    
    def get_page_source(self):
        """
        Get the current page source after JavaScript execution
        
        Returns:
            str: HTML content of the page
        """
        return self.driver.page_source
    
    def get_page_title(self):
        """
        Extract the page title
        
        Returns:
            str: Page title
        """
        return self.driver.title
    
    def get_headlines(self):
        """
        Extract all h1, h2, and h3 headlines from the page
        
        Returns:
            dict: Dictionary with headline tags as keys and lists of headlines as values
        """
        headlines = {
            'h1': [],
            'h2': [],
            'h3': []
        }
        
        for tag in headlines.keys():
            elements = self.driver.find_elements(By.TAG_NAME, tag)
            headlines[tag] = [element.text for element in elements if element.text.strip()]
        
        return headlines
    
    def get_text_content(self):
        """
        Extract the main text content from the page
        
        Returns:
            str: Main text content
        """
        try:
            # Use BeautifulSoup to parse the page more effectively
            soup = BeautifulSoup(self.get_page_source(), 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text and normalize whitespace
            text = soup.get_text(separator=' ')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"Error extracting text content: {str(e)}")
            return ""
    
    def get_images(self):
        """
        Extract all images from the page
        
        Returns:
            list: List of dictionaries with image information (url, alt text)
        """
        images = []
        
        try:
            elements = self.driver.find_elements(By.TAG_NAME, "img")
            
            for element in elements:
                try:
                    src = element.get_attribute("src")
                    alt = element.get_attribute("alt") or ""
                    
                    if src:
                        images.append({
                            'url': src,
                            'alt': alt
                        })
                except:
                    continue
        except Exception as e:
            print(f"Error extracting images: {str(e)}")
        
        return images


# Convenience functions
def scrape_url(url, headless=True, browser='auto'):
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

def get_page_title(url, headless=True, browser='auto'):
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

def get_headlines(url, headless=True, browser='auto'):
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

def get_text_content(url, headless=True, browser='auto'):
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

def get_images(url, headless=True, browser='auto'):
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
    
    return crawler.get_images()