"""
WebDriverFactory module for creating and configuring WebDriver instances.
This module handles browser initialization and configuration.
"""
import platform
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# Setup basic logging
logger = logging.getLogger(__name__)

class WebDriverFactory:
    """
    Factory for creating WebDriver instances with appropriate configuration.
    """
    
    @staticmethod
    def create_driver(browser_type='auto', headless=True):
        """
        Create and return a configured WebDriver instance.
        
        Args:
            browser_type (str): Browser to use ('chrome', 'firefox', or 'auto')
            headless (bool): Run browser in headless mode if True
            
        Returns:
            WebDriver: Configured WebDriver instance
            
        Raises:
            ValueError: If browser_type is unsupported
            WebDriverException: If browser initialization fails
        """
        # Detect system architecture
        system = platform.system().lower()
        is_arm = platform.machine().lower() in ('arm', 'arm64', 'aarch64')
        
        # Try to initialize with the selected browser or fallback to available ones
        if browser_type == 'auto' or browser_type == 'chrome':
            try:
                driver = WebDriverFactory._setup_chrome(headless, system, is_arm)
                return driver
            except WebDriverException as e:
                logger.warning(f"Failed to initialize Chrome: {str(e)}")
                if browser_type == 'auto':
                    logger.info("Trying Firefox instead")
                    return WebDriverFactory._setup_firefox(headless)
                else:
                    raise
        elif browser_type == 'firefox':
            return WebDriverFactory._setup_firefox(headless)
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")
    
    @staticmethod
    def _setup_chrome(headless, system, is_arm):
        """
        Setup Chrome WebDriver with appropriate options.
        
        Args:
            headless (bool): Run in headless mode if True
            system (str): Operating system name
            is_arm (bool): True if running on ARM architecture
            
        Returns:
            WebDriver: Configured Chrome WebDriver instance
        """
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
        if is_arm and system == 'darwin':
            logger.info("Detected macOS ARM architecture")
            chrome_version = ChromeDriverManager().driver.get_latest_release_version()
            options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            # Initialize the WebDriver
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager(driver_version=chrome_version).install()),
                options=options
            )
        else:
            # Standard initialization
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options
            )
        
        logger.info("Chrome WebDriver initialized successfully")
        return driver
        
    @staticmethod
    def _setup_firefox(headless):
        """
        Setup Firefox WebDriver with appropriate options.
        
        Args:
            headless (bool): Run in headless mode if True
            
        Returns:
            WebDriver: Configured Firefox WebDriver instance
        """
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
        driver = webdriver.Firefox(
            service=FirefoxService(GeckoDriverManager().install()),
            options=options
        )
        
        logger.info("Firefox WebDriver initialized successfully")
        return driver