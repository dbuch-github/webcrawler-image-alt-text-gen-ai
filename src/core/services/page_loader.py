"""
Page loader service responsible for loading web pages and handling consent banners
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)

class PageLoaderService:
    """
    Service for loading web pages and handling cookie consent banners
    """
    
    def __init__(self, driver, timeout=20):
        """
        Initialize the page loader service
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Timeout in seconds for page loading operations
        """
        self.driver = driver
        self.timeout = timeout
    
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
            self.handle_consent_banners()
            
            # Scroll the page to load lazy content
            self.scroll_for_lazy_content()
            
            return True
        
        except TimeoutException:
            logger.error(f"Timeout while loading {url}")
            return False
        except Exception as e:
            logger.error(f"Error loading {url}: {str(e)}")
            return False
    
    def handle_consent_banners(self):
        """
        Identify and accept common consent banners and cookie notices
        
        Returns:
            bool: True if clicked on a consent button, False otherwise
        """
        # List of common consent button identifiers
        consent_identifiers = [
            # Common class names
            ".//button[contains(@class, 'consent') or contains(@class, 'cookie') or contains(@class, 'accept') or contains(@class, 'agree')]",
            ".//a[contains(@class, 'consent') or contains(@class, 'cookie') or contains(@class, 'accept') or contains(@class, 'agree')]",
            ".//div[contains(@class, 'consent') or contains(@class, 'cookie') or contains(@class, 'accept') or contains(@class, 'agree')]",
            
            # Common ID patterns
            ".//*[contains(@id, 'consent') or contains(@id, 'cookie') or contains(@id, 'accept') or contains(@id, 'agree')]",
            
            # Common text in buttons
            ".//button[contains(text(), 'Accept') or contains(text(), 'Agree') or contains(text(), 'OK') or contains(text(), 'Got it')]",
            ".//button[contains(text(), 'accept cookies') or contains(text(), 'accept all') or contains(text(), 'allow cookies')]",
            ".//a[contains(text(), 'Accept') or contains(text(), 'Agree') or contains(text(), 'OK') or contains(text(), 'Got it')]",
            ".//div[contains(text(), 'Accept') or contains(text(), 'Agree') or contains(text(), 'OK') or contains(text(), 'Got it')]",
            ".//span[contains(text(), 'Accept') or contains(text(), 'Agree') or contains(text(), 'OK') or contains(text(), 'Got it')]",
            
            # Common GDPR/cookie specific buttons (case insensitive)
            ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all cookies')]",
            ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept necessary cookies')]",
            ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow all')]",
            ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow cookies')]",
            
            # German consent buttons
            ".//*[contains(text(), 'Akzeptieren') or contains(text(), 'Zustimmen') or contains(text(), 'Einverstanden')]",
            ".//*[contains(text(), 'Alle akzeptieren') or contains(text(), 'Allen zustimmen'or contains(text(), 'Alles Akzeptieren')]",
            
            # French consent buttons
            ".//*[contains(text(), 'Accepter') or contains(text(), 'J\'accepte')]",
            
            # Specific common buttons by role
            ".//button[@aria-label='Accept cookies']",
            ".//button[@aria-label='Accept all cookies']",
            ".//button[@aria-label='Allow cookies']",
            ".//button[@aria-label='Allow all']",
            
            # Specific common buttons by title
            ".//button[@title='Accept cookies']",
            ".//button[@title='Accept all cookies']",
            ".//button[@title='Allow cookies']",
            ".//button[@title='Allow all']",
        ]
        
        # Try each identifier
        clicked_something = False
        for xpath in consent_identifiers:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    try:
                        if element.is_displayed():
                            # Try to scroll to the element to make sure it's visible
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(0.2)  # Small delay after scrolling
                            
                            # Try to click it
                            element.click()
                            clicked_something = True
                            time.sleep(0.5)  # Short wait after click
                    except Exception as e:
                        # If direct click fails, try JavaScript click
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                            clicked_something = True
                            time.sleep(0.5)  # Short wait after click
                        except:
                            pass  # If JS click also fails, continue to next element
            except Exception:
                continue
        
        # Return true if we clicked something
        return clicked_something
    
    def scroll_for_lazy_content(self):
        """
        Scroll the page to trigger lazy loading of images and other content.
        Enhanced with multiple scrolling techniques and proper wait times.
        """
        try:
            # Get the initial page height
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # First approach: Smooth step scrolling with dynamic height updates
            scroll_step = 300
            current_position = 0
            
            while current_position < page_height:
                # Scroll down by step
                current_position += scroll_step
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                
                # Wait longer for content to load
                time.sleep(0.5)
                
                # Check if new content has been loaded (page height increased)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height > page_height:
                    page_height = new_height
                    
                # Don't scroll too many times to avoid infinite loops on some pages
                if current_position > 8000:  # Increased from 5000 to catch longer pages
                    break
            
            # Second approach: Scroll to specific anchors to trigger different lazy-loading mechanisms
            try:
                # Find all elements that might be targets for lazy loading
                potential_anchors = self.driver.find_elements(By.CSS_SELECTOR, "div, section, article, footer, button")
                
                # Take a sample of elements distributed throughout the page
                anchors_to_check = []
                if len(potential_anchors) > 0:
                    step = max(1, len(potential_anchors) // 10)  # Take about 10 elements
                    anchors_to_check = potential_anchors[::step][:10]  # Limit to 10 elements
                
                # Scroll to each anchor
                for anchor in anchors_to_check:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", anchor)
                        time.sleep(0.5)  # Wait for lazy content to load
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error during anchor scrolling: {str(e)}")
            
            # Third approach: Rapid scroll up and down to trigger scroll event listeners
            try:
                # Scroll to bottom quickly
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Scroll back up in larger steps
                height = self.driver.execute_script("return document.body.scrollHeight")
                for pos in range(height, 0, -800):
                    self.driver.execute_script(f"window.scrollTo(0, {pos});")
                    time.sleep(0.2)
            except Exception as e:
                logger.error(f"Error during rapid scrolling: {str(e)}")
            
            # Fourth approach: Trigger scroll events programmatically
            try:
                self.driver.execute_script("""
                    // Dispatch scroll events
                    window.dispatchEvent(new Event('scroll'));
                    document.dispatchEvent(new Event('scroll'));
                    
                    // Trigger any lazy load libraries that might be using these events
                    window.dispatchEvent(new Event('DOMContentLoaded'));
                    window.dispatchEvent(new Event('load'));
                """)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error during event dispatching: {str(e)}")
            
            # Fifth approach: Click on any "load more" buttons
            try:
                # Common patterns for "load more" buttons
                load_more_selectors = [
                    "button[contains(., 'load more')]",
                    "button[contains(., 'mehr laden')]",
                    "button[contains(., 'show more')]",
                    "a[contains(., 'load more')]",
                    "a[contains(., 'mehr laden')]",
                    "div[contains(., 'load more')]",
                    "*[contains(@class, 'load-more')]",
                    "*[contains(@id, 'load-more')]",
                    "*[contains(@class, 'loadMore')]",
                    "*[contains(@id, 'loadMore')]"
                ]
                
                for selector in load_more_selectors:
                    try:
                        load_more_buttons = self.driver.find_elements(By.XPATH, f"//{selector}")
                        for button in load_more_buttons[:2]:  # Limit to first 2 to avoid infinite clicks
                            if button.is_displayed():
                                button.click()
                                time.sleep(1.5)  # Wait for content to load
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error clicking load more buttons: {str(e)}")
            
            # Finally, scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            # Wait a moment for any final loading
            time.sleep(1.5)
            
        except Exception as e:
            logger.error(f"Error during page scrolling: {str(e)}")
    
    def wait_for_network_idle(self, timeout=10, max_connections=0, wait_time=1.0):
        """
        Wait for network to be idle (no active connections)
        
        Args:
            timeout (int): Maximum time to wait in seconds
            max_connections (int): Maximum number of active connections to consider as 'idle'
            wait_time (float): Time to wait after network becomes idle
            
        Returns:
            bool: True if network became idle, False if timed out
        """
        try:
            # Use JavaScript to check network activity
            self.driver.execute_script("""
                window.activeNetworkRequests = 0;
                
                // Override fetch
                const originalFetch = window.fetch;
                window.fetch = function() {
                    window.activeNetworkRequests++;
                    return originalFetch.apply(this, arguments)
                        .then(function(response) {
                            window.activeNetworkRequests--;
                            return response;
                        })
                        .catch(function(error) {
                            window.activeNetworkRequests--;
                            throw error;
                        });
                };
                
                // Override XMLHttpRequest
                const originalXHROpen = XMLHttpRequest.prototype.open;
                const originalXHRSend = XMLHttpRequest.prototype.send;
                
                XMLHttpRequest.prototype.open = function() {
                    this._networkRequest = true;
                    return originalXHROpen.apply(this, arguments);
                };
                
                XMLHttpRequest.prototype.send = function() {
                    if (this._networkRequest) {
                        window.activeNetworkRequests++;
                        this.addEventListener('loadend', function() {
                            window.activeNetworkRequests--;
                        });
                    }
                    return originalXHRSend.apply(this, arguments);
                };
            """)
            
            # Wait for network to be idle
            start_time = time.time()
            while time.time() - start_time < timeout:
                active_requests = self.driver.execute_script("return window.activeNetworkRequests || 0;")
                if active_requests <= max_connections:
                    # Network appears idle, wait a bit to ensure completion
                    time.sleep(wait_time)
                    
                    # Check again to confirm idle state persists
                    active_requests = self.driver.execute_script("return window.activeNetworkRequests || 0;")
                    if active_requests <= max_connections:
                        logger.info(f"Network idle detected after {time.time() - start_time:.2f} seconds")
                        return True
                        
                time.sleep(0.3)  # Poll every 300ms
                
            logger.warning(f"Network idle wait timed out after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Error waiting for network idle: {str(e)}")
            return False