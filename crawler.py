import time
import platform
import logging
import tempfile
import re
import requests
from urllib.parse import urlparse, urljoin
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
            
            # Scroll the page to load lazy content
            self._scroll_for_lazy_content()
            
            return True
        
        except TimeoutException:
            print(f"Timeout while loading {url}")
            return False
        except Exception as e:
            print(f"Error loading {url}: {str(e)}")
            return False
    
    def _scroll_for_lazy_content(self):
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
                
                # Wait longer for content to load (increased from 0.3s)
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
                print(f"Error during anchor scrolling: {str(e)}")
            
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
                print(f"Error during rapid scrolling: {str(e)}")
            
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
                print(f"Error during event dispatching: {str(e)}")
            
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
                print(f"Error clicking load more buttons: {str(e)}")
            
            # Finally, scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            # Wait a moment for any final loading (increased to allow network requests to complete)
            time.sleep(1.5)
            
        except Exception as e:
            print(f"Error during page scrolling: {str(e)}")
    
    def _handle_consent_banners(self):
        """
        Identify and accept common consent banners and cookie notices
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
        Extract all h1, h2, and h3 headlines from the page with their identifiers
        
        Returns:
            dict: Dictionary with headline tags as keys and lists of headline info as values
        """
        headlines = {
            'h1': [],
            'h2': [],
            'h3': []
        }
        
        # Get the current page URL
        current_url = self.driver.current_url
        
        for tag in headlines.keys():
            elements = self.driver.find_elements(By.TAG_NAME, tag)
            for element in elements:
                if element.text.strip():
                    # Get the element's ID if available
                    element_id = element.get_attribute('id')
                    
                    # If no ID, try to create a unique identifier
                    anchor = None
                    if element_id:
                        anchor = f"#{element_id}"
                    else:
                        # Try to get the element's class
                        element_class = element.get_attribute('class')
                        
                        # Try to create a JavaScript-based selector
                        try:
                            # Create a unique xpath to the element
                            xpath = self.driver.execute_script("""
                                function getPathTo(element) {
                                    if (element.id !== '')
                                        return '//*[@id="' + element.id + '"]';
                                    if (element === document.body)
                                        return '/html/body';

                                    var index = 0;
                                    var siblings = element.parentNode.childNodes;
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sibling = siblings[i];
                                        if (sibling === element)
                                            return getPathTo(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (index + 1) + ']';
                                        if (sibling.nodeType === 1 && sibling.tagName.toLowerCase() === element.tagName.toLowerCase())
                                            index++;
                                    }
                                }
                                return getPathTo(arguments[0]);
                            """, element)
                        except:
                            xpath = None
                    
                    # Add headline info to the list
                    headlines[tag].append({
                        'text': element.text,
                        'id': element_id,
                        'class': element.get_attribute('class'),
                        'xpath': xpath,
                        'url': current_url + (anchor if anchor else '')
                    })
        
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
        Extract all images from the page using multiple methods
        
        Returns:
            list: List of dictionaries with image information (url, alt text)
        """
        images = []
        image_urls = set()  # To track unique URLs
        
        try:
            # Ensure the page is fully loaded with all dynamic content
            self._wait_for_network_idle()
            
            # Method 1: Find all <img> tags using Selenium
            elements = self.driver.find_elements(By.TAG_NAME, "img")
            
            for element in elements:
                try:
                    # Try different attributes where image URLs might be stored
                    src = element.get_attribute("src")
                    data_src = element.get_attribute("data-src")
                    data_lazy_src = element.get_attribute("data-lazy-src")
                    srcset = element.get_attribute("srcset")
                    
                    # Additional CDN-specific attributes
                    data_cdn = element.get_attribute("data-cdn")
                    data_srcset = element.get_attribute("data-srcset")
                    data_original = element.get_attribute("data-original")
                    data_bg = element.get_attribute("data-bg")
                    data_background = element.get_attribute("data-background")
                    data_poster = element.get_attribute("data-poster")
                    
                    # Collect even more data attributes that might contain image URLs
                    additional_attrs = [
                        "data-src-retina", "data-lazy-original", "data-echo", "data-img-url",
                        "data-delay-src", "data-hero", "data-low-res-src", "data-path", 
                        "data-thumbs", "data-l", "data-m", "data-xl", "data-xxl"
                    ]
                    additional_data = {}
                    for attr in additional_attrs:
                        val = element.get_attribute(attr)
                        if val:
                            additional_data[attr] = val
                    
                    # Get alt text and other metadata
                    alt = element.get_attribute("alt") or ""
                    title = element.get_attribute("title") or ""
                    aria_label = element.get_attribute("aria-label") or ""
                    
                    # Process the main source if available
                    if src and src not in image_urls and not src.startswith("data:"):
                        image_urls.add(src)
                        images.append({
                            'url': src,
                            'alt': alt,
                            'title': title,
                            'aria_label': aria_label,
                            'type': 'img'
                        })
                    
                    # Process data-src (lazy loading)
                    if data_src and data_src not in image_urls and not data_src.startswith("data:"):
                        image_urls.add(data_src)
                        images.append({
                            'url': data_src,
                            'alt': alt,
                            'title': title,
                            'aria_label': aria_label,
                            'type': 'img-lazy'
                        })
                    
                    # Process data-lazy-src (another lazy loading variant)
                    if data_lazy_src and data_lazy_src not in image_urls and not data_lazy_src.startswith("data:"):
                        image_urls.add(data_lazy_src)
                        images.append({
                            'url': data_lazy_src,
                            'alt': alt,
                            'title': title,
                            'aria_label': aria_label,
                            'type': 'img-lazy'
                        })
                    
                    # Process CDN-specific attributes
                    for attr_name, attr_value in [
                        ('data-cdn', data_cdn),
                        ('data-original', data_original),
                        ('data-bg', data_bg),
                        ('data-background', data_background),
                        ('data-poster', data_poster)
                    ]:
                        if attr_value and attr_value not in image_urls and not attr_value.startswith("data:"):
                            image_urls.add(attr_value)
                            images.append({
                                'url': attr_value,
                                'alt': alt,
                                'title': title,
                                'aria_label': aria_label,
                                'type': f'img-{attr_name}'
                            })
                    
                    # Process additional data attributes
                    for attr_name, attr_value in additional_data.items():
                        if attr_value and attr_value not in image_urls and not attr_value.startswith("data:"):
                            image_urls.add(attr_value)
                            images.append({
                                'url': attr_value,
                                'alt': alt,
                                'title': title,
                                'aria_label': aria_label,
                                'type': f'img-{attr_name}'
                            })
                    
                    # Process srcset (responsive images)
                    for srcset_attr in [srcset, data_srcset]:
                        if srcset_attr:
                            try:
                                # Parse srcset attribute which can contain multiple URLs
                                srcset_parts = srcset_attr.split(',')
                                for part in srcset_parts:
                                    url_width = part.strip().split(' ')
                                    if len(url_width) >= 1:
                                        srcset_url = url_width[0].strip()
                                        if srcset_url and srcset_url not in image_urls and not srcset_url.startswith("data:"):
                                            image_urls.add(srcset_url)
                                            images.append({
                                                'url': srcset_url,
                                                'alt': alt,
                                                'title': title,
                                                'aria_label': aria_label,
                                                'type': 'srcset'
                                            })
                            except:
                                pass  # Skip if srcset parsing fails
                except:
                    continue
            
            # Method 2: Find background images in style attributes
            try:
                # Find elements with background-image style
                elements_with_bg = self.driver.find_elements(By.XPATH, "//*[contains(@style, 'background')]")
                
                for element in elements_with_bg:
                    try:
                        style = element.get_attribute("style")
                        if style and 'url(' in style:
                            # Extract URL from background-image: url('...')
                            bg_url_matches = re.findall(r"url\(['\"]?(.*?)['\"]?\)", style)
                            for bg_url in bg_url_matches:
                                if bg_url and bg_url not in image_urls and not bg_url.startswith("data:"):
                                    image_urls.add(bg_url)
                                    images.append({
                                        'url': bg_url,
                                        'alt': element.get_attribute("alt") or element.get_attribute("title") or element.get_attribute("aria-label") or "",
                                        'title': element.get_attribute("title") or "",
                                        'aria_label': element.get_attribute("aria-label") or "",
                                        'type': 'background'
                                    })
                    except:
                        continue
            except:
                pass  # Skip if background image extraction fails
            
            # Method 3: Use BeautifulSoup for additional parsing
            try:
                soup = BeautifulSoup(self.get_page_source(), 'html.parser')
                
                # Find picture elements (modern responsive images)
                picture_elements = soup.find_all('picture')
                for picture in picture_elements:
                    # Get source elements within picture
                    source_elements = picture.find_all('source')
                    for source in source_elements:
                        if source.has_attr('srcset'):
                            srcset = source['srcset']
                            srcset_parts = srcset.split(',')
                            for part in srcset_parts:
                                url_width = part.strip().split(' ')
                                if len(url_width) >= 1:
                                    srcset_url = url_width[0].strip()
                                    if srcset_url and srcset_url not in image_urls and not srcset_url.startswith("data:"):
                                        image_urls.add(srcset_url)
                                        # Try to get alt text from the img element within the picture
                                        alt_text = ""
                                        title_text = ""
                                        img_element = picture.find('img')
                                        if img_element:
                                            alt_text = img_element.get('alt', '')
                                            title_text = img_element.get('title', '')
                                        
                                        images.append({
                                            'url': srcset_url,
                                            'alt': alt_text or source.get('alt', ''),
                                            'title': title_text or source.get('title', ''),
                                            'type': 'picture-source'
                                        })
                
                # Find CSS with background images
                style_tags = soup.find_all('style')
                for style_tag in style_tags:
                    style_content = style_tag.string
                    if style_content:
                        # Find all background patterns with url(...) 
                        bg_patterns = [
                            r"background-image:\s*url\(['\"]?(.*?)['\"]?\)",
                            r"background:\s*.*?url\(['\"]?(.*?)['\"]?\)",
                            r"background-[a-z]+:\s*.*?url\(['\"]?(.*?)['\"]?\)"
                        ]
                        
                        for pattern in bg_patterns:
                            bg_urls = re.findall(pattern, style_content)
                            for bg_url in bg_urls:
                                if bg_url and bg_url not in image_urls and not bg_url.startswith("data:"):
                                    image_urls.add(bg_url)
                                    images.append({
                                        'url': bg_url,
                                        'alt': '',
                                        'title': '',
                                        'type': 'css-background'
                                    })
            except Exception as e:
                print(f"Error in BeautifulSoup parsing: {str(e)}")
                
            # Method 4: Check for Shadow DOM content
            try:
                # Find all elements that might have a shadow root
                potential_shadow_hosts = self.driver.find_elements(By.CSS_SELECTOR, "*")
                
                for host in potential_shadow_hosts[:100]:  # Limit to prevent checking every element
                    try:
                        # Check if element has shadow root
                        shadow_root = self.driver.execute_script("return arguments[0].shadowRoot", host)
                        if shadow_root:
                            # Find images within shadow DOM
                            shadow_images = self.driver.execute_script("""
                                var root = arguments[0].shadowRoot;
                                var images = Array.from(root.querySelectorAll('img'));
                                return images.map(function(img) {
                                    return {
                                        src: img.src,
                                        dataSrc: img.getAttribute('data-src'),
                                        srcset: img.getAttribute('srcset'),
                                        alt: img.getAttribute('alt') || '',
                                        title: img.getAttribute('title') || ''
                                    };
                                });
                            """, host)
                            
                            if shadow_images:
                                for img_data in shadow_images:
                                    # Process the shadow DOM images
                                    for url_key in ['src', 'dataSrc']:
                                        if img_data.get(url_key) and img_data[url_key] not in image_urls and not img_data[url_key].startswith("data:"):
                                            url = img_data[url_key]
                                            image_urls.add(url)
                                            images.append({
                                                'url': url,
                                                'alt': img_data.get('alt', ''),
                                                'title': img_data.get('title', ''),
                                                'type': 'shadow-dom-img',
                                                'from_shadow_dom': True
                                            })
                            
                            # Also check for background images in shadow DOM
                            shadow_bg_elements = self.driver.execute_script("""
                                var root = arguments[0].shadowRoot;
                                var elements = Array.from(root.querySelectorAll('*[style*="background"]'));
                                return elements.map(function(el) {
                                    return el.getAttribute('style') || '';
                                });
                            """, host)
                            
                            if shadow_bg_elements:
                                for style in shadow_bg_elements:
                                    if 'url(' in style:
                                        bg_url_matches = re.findall(r"url\(['\"]?(.*?)['\"]?\)", style)
                                        for bg_url in bg_url_matches:
                                            if bg_url and bg_url not in image_urls and not bg_url.startswith("data:"):
                                                image_urls.add(bg_url)
                                                images.append({
                                                    'url': bg_url,
                                                    'alt': '',
                                                    'title': '',
                                                    'type': 'shadow-dom-background',
                                                    'from_shadow_dom': True
                                                })
                    except:
                        continue
            except Exception as e:
                print(f"Error checking Shadow DOM: {str(e)}")
                
            # Method 5: Check for common image galleries
            try:
                # Extended gallery selector to catch more gallery types
                gallery_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//*[contains(@class, 'gallery') or contains(@class, 'slider') or contains(@class, 'carousel') or " +
                    "contains(@id, 'gallery') or contains(@id, 'slider') or contains(@id, 'carousel') or " +
                    "contains(@data-gallery, 'true') or contains(@data-slider, 'true') or contains(@data-role, 'carousel')]"
                )
                
                for gallery in gallery_elements:
                    # Find all elements with data-attributes that might contain image URLs
                    data_elements = gallery.find_elements(
                        By.XPATH, 
                        ".//*[@data-src or @data-full or @data-image or @data-lazy or @data-thumb or " +
                        "@data-srcset or @data-slide-bg or @data-bg or @data-large or @data-medium or " +
                        "@data-original or @data-background or @data-id or @data-i]"
                    )
                    
                    for element in data_elements:
                        try:
                            # Check various data attributes for image URLs
                            for attr in [
                                'data-src', 'data-full', 'data-image', 'data-lazy', 'data-thumb',
                                'data-large', 'data-medium', 'data-original', 'data-slide-bg',
                                'data-bg', 'data-background', 'data-hero-image', 'data-i', 'data-id'
                            ]:
                                url = element.get_attribute(attr)
                                if url and url not in image_urls and not url.startswith("data:"):
                                    # Check if it's actually an image URL and not just an ID
                                    if ('/' in url or '.' in url) or attr in ['data-src', 'data-image', 'data-full']:
                                        image_urls.add(url)
                                        images.append({
                                            'url': url,
                                            'alt': element.get_attribute("alt") or element.get_attribute("title") or element.get_attribute("aria-label") or "",
                                            'title': element.get_attribute("title") or "",
                                            'aria_label': element.get_attribute("aria-label") or "",
                                            'type': f'gallery-{attr}'
                                        })
                        except:
                            continue
            except:
                pass  # Skip if gallery extraction fails
            
            # Method 6: Check for sliders and carousels specially
            try:
                # Check for slider libraries
                slider_selectors = [
                    "//*[contains(@class, 'swiper') or contains(@class, 'slick') or contains(@class, 'owl')]",
                    "//*[contains(@data-slick, '{') or contains(@data-swiper, '{') or contains(@data-owl, '{')]"
                ]
                
                for selector in slider_selectors:
                    slider_elements = self.driver.find_elements(By.XPATH, selector)
                    for slider in slider_elements:
                        try:
                            # Find all potential slides
                            slides = slider.find_elements(By.XPATH, ".//*[contains(@class, 'slide') or contains(@class, 'item')]")
                            
                            for slide in slides:
                                # Look for images or backgrounds in slides
                                imgs = slide.find_elements(By.TAG_NAME, "img")
                                for img in imgs:
                                    src = img.get_attribute("src")
                                    if src and src not in image_urls and not src.startswith("data:"):
                                        image_urls.add(src)
                                        images.append({
                                            'url': src,
                                            'alt': img.get_attribute("alt") or "",
                                            'title': img.get_attribute("title") or "",
                                            'aria_label': img.get_attribute("aria-label") or "",
                                            'type': 'slider-img'
                                        })
                                
                                # Check for background image in slide
                                style = slide.get_attribute("style")
                                if style and 'url(' in style:
                                    bg_url_matches = re.findall(r"url\(['\"]?(.*?)['\"]?\)", style)
                                    for bg_url in bg_url_matches:
                                        if bg_url and bg_url not in image_urls and not bg_url.startswith("data:"):
                                            image_urls.add(bg_url)
                                            images.append({
                                                'url': bg_url,
                                                'alt': slide.get_attribute("alt") or slide.get_attribute("title") or "",
                                                'title': slide.get_attribute("title") or "",
                                                'aria_label': slide.get_attribute("aria-label") or "",
                                                'type': 'slider-background'
                                            })
                        except:
                            continue
            except:
                pass  # Skip if slider extraction fails
            
            # Method 7: Check for images in iframes (common for CDN-hosted content)
            try:
                # Find all iframes and extended to more attributes
                iframes = self.driver.find_elements(By.XPATH, "//iframe | //frame")
                
                # Store the current window handle to return to later
                main_window = self.driver.current_window_handle
                
                for iframe in iframes:
                    try:
                        # Get iframe src
                        iframe_src = iframe.get_attribute("src") or iframe.get_attribute("data-src")
                        
                        if not iframe_src:
                            continue
                            
                        # Enhanced logging for iframe inspection
                        print(f"Found iframe with src: {iframe_src}")
                        
                        # Check if iframe is from same origin (to avoid security issues)
                        iframe_domain = urlparse(iframe_src).netloc
                        current_domain = urlparse(self.driver.current_url).netloc
                        
                        # Switch to the iframe
                        try:
                            self.driver.switch_to.frame(iframe)
                            
                            # Wait briefly for iframe content to load
                            time.sleep(0.5)
                            
                            # Find images within the iframe
                            iframe_images = self.driver.find_elements(By.TAG_NAME, "img")
                            
                            # Enhanced logging for found images
                            print(f"Found {len(iframe_images)} images in iframe {iframe_src}")
                            
                            for img in iframe_images:
                                try:
                                    # Check multiple source attributes
                                    for src_attr in ['src', 'data-src', 'data-lazy-src']:
                                        src = img.get_attribute(src_attr)
                                        if src and src not in image_urls and not src.startswith("data:"):
                                            image_urls.add(src)
                                            images.append({
                                                'url': src,
                                                'alt': img.get_attribute("alt") or "",
                                                'title': img.get_attribute("title") or "",
                                                'aria_label': img.get_attribute("aria-label") or "",
                                                'type': f'iframe-img-{src_attr}',
                                                'from_iframe': True,
                                                'iframe_src': iframe_src
                                            })
                                    
                                    # Check srcset as well
                                    srcset = img.get_attribute("srcset")
                                    if srcset:
                                        srcset_parts = srcset.split(',')
                                        for part in srcset_parts:
                                            url_width = part.strip().split(' ')
                                            if len(url_width) >= 1:
                                                srcset_url = url_width[0].strip()
                                                if srcset_url and srcset_url not in image_urls and not srcset_url.startswith("data:"):
                                                    image_urls.add(srcset_url)
                                                    images.append({
                                                        'url': srcset_url,
                                                        'alt': img.get_attribute("alt") or "",
                                                        'title': img.get_attribute("title") or "",
                                                        'aria_label': img.get_attribute("aria-label") or "",
                                                        'type': 'iframe-srcset',
                                                        'from_iframe': True,
                                                        'iframe_src': iframe_src
                                                    })
                                except:
                                    continue
                            
                            # Also check for background images in the iframe
                            try:
                                elements_with_bg = self.driver.find_elements(By.XPATH, "//*[contains(@style, 'background')]")
                                
                                for element in elements_with_bg:
                                    try:
                                        style = element.get_attribute("style")
                                        if style and 'url(' in style:
                                            # Extract URL from background-image: url('...')
                                            bg_url_matches = re.findall(r"url\(['\"]?(.*?)['\"]?\)", style)
                                            for bg_url in bg_url_matches:
                                                if bg_url and bg_url not in image_urls and not bg_url.startswith("data:"):
                                                    image_urls.add(bg_url)
                                                    images.append({
                                                        'url': bg_url,
                                                        'alt': element.get_attribute("alt") or element.get_attribute("title") or "",
                                                        'title': element.get_attribute("title") or "",
                                                        'aria_label': element.get_attribute("aria-label") or "",
                                                        'type': 'iframe-background',
                                                        'from_iframe': True,
                                                        'iframe_src': iframe_src
                                                    })
                                    except:
                                        continue
                            except:
                                pass
                                
                            # Switch back to the main content
                            self.driver.switch_to.default_content()
                        except Exception as e:
                            print(f"Error switching to iframe or processing its content: {str(e)}")
                            # Make sure we switch back to the main content even if there's an error
                            try:
                                self.driver.switch_to.default_content()
                            except:
                                pass
                    except Exception as e:
                        print(f"Error processing iframe: {str(e)}")
                        # Make sure we switch back to the main content even if there's an error
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
            except Exception as e:
                print(f"Error processing iframes: {str(e)}")
                # Make sure we switch back to the main content even if there's an error
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
            
            # Method 8: Check for dynamically generated content using JavaScript
            try:
                # Execute JavaScript to find images that might be hidden in JavaScript variables
                js_images = self.driver.execute_script("""
                    var images = [];
                    
                    // Function to extract URLs from JavaScript objects and arrays
                    function findImagesInObject(obj, depth) {
                        if (depth > 5) return []; // Prevent infinite recursion
                        if (!obj) return [];
                        
                        var results = [];
                        
                        if (typeof obj === 'string') {
                            // Check if string is a URL
                            if (obj.match(/\\.(jpg|jpeg|png|gif|webp|svg)(\\?.*)?$/i)) {
                                results.push(obj);
                            }
                        } else if (Array.isArray(obj)) {
                            // Search through arrays
                            for (var i = 0; i < obj.length; i++) {
                                results = results.concat(findImagesInObject(obj[i], depth + 1));
                            }
                        } else if (typeof obj === 'object') {
                            // Search through object properties
                            for (var key in obj) {
                                // Look for properties that might contain image URLs
                                if (key.match(/(image|img|thumb|src|source|url|background)/i)) {
                                    results = results.concat(findImagesInObject(obj[key], depth + 1));
                                }
                                
                                // Also check all values
                                if (results.length < 100) { // Limit to prevent too much processing
                                    results = results.concat(findImagesInObject(obj[key], depth + 1));
                                }
                            }
                        }
                        
                        return results;
                    }
                    
                    // Check common JavaScript variables
                    var jsVars = ['images', 'gallery', 'photos', 'slides', 'carouselItems', 'productImages', 'thumbnails'];
                    for (var i = 0; i < jsVars.length; i++) {
                        if (window[jsVars[i]]) {
                            images = images.concat(findImagesInObject(window[jsVars[i]], 0));
                        }
                    }
                    
                    // Check other global variables that might contain image data
                    for (var varName in window) {
                        if (varName.match(/(image|img|gallery|slide|carousel|media)/i)) {
                            if (images.length < 200) { // Limit to prevent too much processing
                                images = images.concat(findImagesInObject(window[varName], 0));
                            }
                        }
                    }
                    
                    return images;
                """)
                
                if js_images:
                    for js_url in js_images:
                        if js_url and js_url not in image_urls and not js_url.startswith("data:"):
                            image_urls.add(js_url)
                            images.append({
                                'url': js_url,
                                'alt': "",
                                'title': "",
                                'type': 'js-extracted'
                            })
            except Exception as e:
                print(f"Error extracting JS images: {str(e)}")
            
            # Process and normalize URLs
            normalized_images = []
            base_url = self.driver.current_url
            parsed_base = urlparse(base_url)
            base_domain = parsed_base.netloc
            
            for img in images:
                try:
                    # Handle relative URLs
                    if img['url'].startswith('//'):  # Protocol-relative URL
                        img['url'] = f"{parsed_base.scheme}:{img['url']}"
                    elif img['url'].startswith('/'):  # Root-relative URL
                        img['url'] = f"{parsed_base.scheme}://{parsed_base.netloc}{img['url']}"
                    elif not img['url'].startswith(('http://', 'https://')):  # Relative URL
                        img['url'] = urljoin(base_url, img['url'])
                    
                    # Ensure the URL is valid
                    parsed_img_url = urlparse(img['url'])
                    if not parsed_img_url.netloc:  # If domain is missing
                        img['url'] = f"{parsed_base.scheme}://{parsed_base.netloc}/{img['url'].lstrip('/')}"
                    
                    # Clean up any URL encoding issues
                    img['url'] = img['url'].replace(' ', '%20')
                    
                    # Add debugging info for CDN domains
                    img_domain = urlparse(img['url']).netloc
                    # Estimate image size
                    try:
                        response = requests.head(img['url'], timeout=3)
                        if 'content-length' in response.headers:
                            size_kb = round(int(response.headers['content-length']) / 1024, 2)
                        else:
                            size_kb = "unknown"
                    except:
                        size_kb = "error"
                    
                    if img_domain and img_domain != base_domain:
                        print(f"Found image from different domain: {img_domain} (base: {base_domain})\nImage URL: {img['url']}\nEstimated size: {size_kb} KB")
                        # Mark the image as coming from a CDN domain
                        img['from_cdn'] = True
                    else:
                        img['from_cdn'] = False
                        
                    # Mark if the image is from an iframe (based on the type)
                    if 'iframe' in img.get('type', ''):
                        img['from_iframe'] = True
                    else:
                        img['from_iframe'] = False
                    
                    normalized_images.append(img)
                except Exception as e:
                    print(f"Error normalizing URL {img.get('url', 'unknown')}: {str(e)}")
                    # Keep the original URL if normalization fails
                    normalized_images.append(img)
            
            # Deduplicate responsive images (same image in different sizes)
            deduplicated_images = self._deduplicate_responsive_images(normalized_images)
            
            # Add debug information about deduplication
            print(f"Found {len(images)} total images, normalized to {len(normalized_images)}, deduplicated to {len(deduplicated_images)}")
            
            return deduplicated_images
            
        except Exception as e:
            print(f"Error extracting images: {str(e)}")
            return images
            
    def _wait_for_network_idle(self, timeout=10, max_connections=0, wait_time=1.0):
        """
        Wait for network to be idle (no active connections)
        
        Args:
            timeout (int): Maximum time to wait in seconds
            max_connections (int): Maximum number of active connections to consider as 'idle'
            wait_time (float): Time to wait after network becomes idle
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
                        print(f"Network idle detected after {time.time() - start_time:.2f} seconds")
                        return True
                        
                time.sleep(0.3)  # Poll every 300ms
                
            print(f"Network idle wait timed out after {timeout} seconds")
            return False
        except Exception as e:
            print(f"Error waiting for network idle: {str(e)}")
            return False
        
    def _deduplicate_responsive_images(self, images):
        """
        Identify and deduplicate responsive images (same image in different sizes)
        
        Args:
            images (list): List of image dictionaries
            
        Returns:
            list: Deduplicated list of images with the best version of each image
        """
        if not images:
            return []
            
        # Group images by base filename (without size indicators)
        image_groups = {}
        
        for img in images:
            # Skip if URL is missing
            if not img.get('url'):
                continue
                
            url = img['url']
            
            # Extract the base part of the filename
            try:
                # Parse the URL
                parsed_url = urlparse(url)
                path = parsed_url.path
                domain = parsed_url.netloc
                
                # Get the filename
                filename = path.split('/')[-1]
                
                # Remove common size indicators from filename
                # Examples: image-800x600.jpg, image_large.png, image-thumbnail.jpg, image@2x.jpg
                base_name = re.sub(r'[-_](\d+x\d+|small|medium|large|thumbnail|thumb|\d+w|\d+h|\d+px|@\d+x)\b', '', filename)
                base_name = re.sub(r'@\d+x', '', base_name)  # Handle @2x, @3x notation
                
                # Create a signature based on the path without size indicators
                path_signature = path.replace(filename, base_name)
                
                # Also consider the alt text for grouping
                alt_text = img.get('alt', '')
                
                # Create a group key that includes domain information
                # This helps distinguish between same-named images on different domains
                # For CDN domains, we try to extract the base domain to group related CDNs together
                domain_parts = domain.split('.')
                
                # Handle CDN subdomains (like cdn.example.com, img.example.com, etc.)
                if len(domain_parts) > 2:
                    # Check for common CDN prefixes
                    if domain_parts[0] in ['cdn', 'img', 'images', 'static', 'media', 'assets']:
                        # Use the base domain (example.com) for grouping
                        base_domain = '.'.join(domain_parts[-2:])
                    else:
                        # Use the full domain
                        base_domain = domain
                else:
                    base_domain = domain
                
                # Create a group key based on the domain, path and alt text
                group_key = f"{base_domain}{path_signature}_{alt_text}"
                
                if group_key not in image_groups:
                    image_groups[group_key] = []
                    
                image_groups[group_key].append(img)
            except Exception as e:
                print(f"Error during image deduplication: {str(e)}")
                # If we can't parse the URL, just add it as is
                random_key = f"unparsed_{len(image_groups)}"
                if random_key not in image_groups:
                    image_groups[random_key] = []
                image_groups[random_key].append(img)
        
        # Select the best image from each group
        deduplicated = []
        
        for group_key, group_images in image_groups.items():
            if len(group_images) == 1:
                # If there's only one image in the group, add it as is
                deduplicated.append(group_images[0])
            else:
                # For multiple images, select the best one based on heuristics
                best_image = self._select_best_image(group_images)
                deduplicated.append(best_image)
        
        return deduplicated
    
    def scroll_page(self):
        """
        Scroll the page to trigger lazy-loaded content
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
            print(f"Error scrolling page: {str(e)}")
            return False
            
    def get_images_from_iframes(self):
        """
        Extract images from all iframes on the page
        
        Returns:
            list: List of image dictionaries from iframes
        """
        iframe_images = []
        
        try:
            # Find all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            if not iframes:
                return []
                
            print(f"Found {len(iframes)} iframes to check for images")
            
            # Store the current window handle to return to later
            main_window = self.driver.current_window_handle
            
            for iframe in iframes:
                try:
                    # Get iframe src
                    iframe_src = iframe.get_attribute("src")
                    
                    if not iframe_src:
                        continue
                        
                    print(f"Checking iframe with src: {iframe_src}")
                    
                    # Switch to the iframe
                    self.driver.switch_to.frame(iframe)
                    
                    # Find images within the iframe
                    iframe_img_elements = self.driver.find_elements(By.TAG_NAME, "img")
                    
                    # Base URL for resolving relative URLs
                    base_url = iframe_src
                    parsed_base = urlparse(base_url)
                    base_domain = parsed_base.netloc
                    
                    for img in iframe_img_elements:
                        try:
                            src = img.get_attribute("src")
                            data_src = img.get_attribute("data-src")
                            data_lazy_src = img.get_attribute("data-lazy-src")
                            
                            # Additional CDN-specific attributes
                            data_cdn = img.get_attribute("data-cdn")
                            data_srcset = img.get_attribute("data-srcset")
                            data_original = img.get_attribute("data-original")
                            
                            # Get alt text and other metadata
                            alt = img.get_attribute("alt") or ""
                            title = img.get_attribute("title") or ""
                            
                            # Process all possible image sources
                            for attr_name, attr_value in [
                                ('src', src),
                                ('data-src', data_src),
                                ('data-lazy-src', data_lazy_src),
                                ('data-cdn', data_cdn),
                                ('data-srcset', data_srcset),
                                ('data-original', data_original)
                            ]:
                                if attr_value and not attr_value.startswith("data:"):
                                    # Normalize URL
                                    url = attr_value
                                    if url.startswith('//'):
                                        url = f"{parsed_base.scheme}:{url}"
                                    elif url.startswith('/'):
                                        url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                                    elif not url.startswith(('http://', 'https://')):
                                        url = urljoin(base_url, url)
                                    
                                    # Check if from CDN domain
                                    img_domain = urlparse(url).netloc
                                    from_cdn = img_domain and img_domain != base_domain
                                    
                                    # Add to results
                                    iframe_images.append({
                                        'url': url,
                                        'alt': alt,
                                        'title': title,
                                        'type': f'iframe-{attr_name}',
                                        'from_iframe': True,
                                        'from_cdn': from_cdn
                                    })
                        except Exception as e:
                            print(f"Error processing iframe image: {str(e)}")
                            continue
                    
                    # Also check for background images in the iframe
                    try:
                        elements_with_bg = self.driver.find_elements(By.XPATH, "//*[contains(@style, 'background-image')]")
                        
                        for element in elements_with_bg:
                            try:
                                style = element.get_attribute("style")
                                if style and 'url(' in style:
                                    # Extract URL from background-image: url('...')
                                    bg_url_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                                    if bg_url_match:
                                        bg_url = bg_url_match.group(1)
                                        if bg_url and not bg_url.startswith("data:"):
                                            # Normalize URL
                                            if bg_url.startswith('//'):
                                                bg_url = f"{parsed_base.scheme}:{bg_url}"
                                            elif bg_url.startswith('/'):
                                                bg_url = f"{parsed_base.scheme}://{parsed_base.netloc}{bg_url}"
                                            elif not bg_url.startswith(('http://', 'https://')):
                                                bg_url = urljoin(base_url, bg_url)
                                            
                                            # Check if from CDN domain
                                            img_domain = urlparse(bg_url).netloc
                                            from_cdn = img_domain and img_domain != base_domain
                                            
                                            iframe_images.append({
                                                'url': bg_url,
                                                'alt': element.get_attribute("alt") or element.get_attribute("title") or "",
                                                'title': element.get_attribute("title") or "",
                                                'type': 'iframe-background',
                                                'from_iframe': True,
                                                'from_cdn': from_cdn
                                            })
                            except Exception as e:
                                print(f"Error processing iframe background image: {str(e)}")
                                continue
                    except Exception as e:
                        print(f"Error processing iframe background images: {str(e)}")
                    
                    # Switch back to the main content
                    self.driver.switch_to.default_content()
                except Exception as e:
                    print(f"Error processing iframe: {str(e)}")
                    # Make sure we switch back to the main content even if there's an error
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
            
            print(f"Found {len(iframe_images)} images in iframes")
            return iframe_images
            
        except Exception as e:
            print(f"Error extracting images from iframes: {str(e)}")
            # Make sure we switch back to the main content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return []
    
    def _select_best_image(self, images):
        """
        Select the best image from a group of similar images
        
        Args:
            images (list): List of similar image dictionaries
            
        Returns:
            dict: The best image from the group
        """
        if not images:
            return None
            
        # If there's only one image, return it
        if len(images) == 1:
            return images[0]
        
        # Score each image based on various factors
        scored_images = []
        
        for img in images:
            score = 0
            url = img['url']
            
            # Prefer images with meaningful alt text
            if img.get('alt') and len(img.get('alt', '')) > 3:
                score += 10
                
            # Prefer images with title
            if img.get('title') and len(img.get('title', '')) > 3:
                score += 5
                
            # Prefer standard images over background images
            if img.get('type') == 'img':
                score += 15
            elif img.get('type') == 'srcset':
                score += 10
            elif 'background' in img.get('type', ''):
                score += 5
                
            # Look for size indicators in the URL
            size_match = re.search(r'(\d+)x(\d+)', url)
            if size_match:
                width = int(size_match.group(1))
                height = int(size_match.group(2))
                
                # Prefer medium-sized images (not too small, not too large)
                # Ideal size around 800-1200px width
                if 800 <= width <= 1200:
                    score += 20
                elif 500 <= width < 800:
                    score += 15
                elif 1200 < width <= 1600:
                    score += 10
                elif 300 <= width < 500:
                    score += 5
                elif width > 1600:
                    score += 3  # Very large images might be too big
                # Small images get no bonus
                
            # Look for size indicators in the filename
            if 'large' in url.lower():
                score += 8
            elif 'medium' in url.lower():
                score += 12
            elif 'small' in url.lower() or 'thumbnail' in url.lower() or 'thumb' in url.lower():
                score -= 5  # Penalize thumbnails
                
            # Prefer original images over scaled ones
            if '@2x' in url or '@3x' in url:
                score -= 3
                
            # Prefer images with standard extensions
            if url.lower().endswith(('.jpg', '.jpeg', '.png')):
                score += 5
            elif url.lower().endswith('.webp'):
                score += 3
                
            scored_images.append((score, img))
        
        # Sort by score (highest first) and return the best image
        scored_images.sort(reverse=True, key=lambda x: x[0])
        return scored_images[0][1]
        
    def take_screenshot(self, output_path=None):
        """
        Take a screenshot of the current page with a browser window size of 1920x1080 pixels
        
        Args:
            output_path (str, optional): Path to save the screenshot. If None, a temporary file is created.
            
        Returns:
            str: Path to the screenshot file
        """
        try:
            if output_path is None:
                # Create a temporary file with .png extension
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                output_path = temp_file.name
                temp_file.close()
            
            # Store original window size
            original_size = self.driver.get_window_size()
            
            # Set window size to 1920x1080
            self.driver.set_window_size(1920, 1080)
            
            # Wait a moment for the page to adjust to the new size
            time.sleep(0.5)
            
            # Take screenshot
            self.driver.save_screenshot(output_path)
            
            # Restore original window size
            self.driver.set_window_size(original_size['width'], original_size['height'])
            
            return output_path
        except Exception as e:
            print(f"Error taking screenshot: {str(e)}")
            return None


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
    
    # Scroll the page to trigger lazy-loaded images
    crawler.scroll_page()
    
    # Get images from main page
    images = crawler.get_images()
    
    # Also get images from iframes
    iframe_images = crawler.get_images_from_iframes()
    if iframe_images:
        images.extend(iframe_images)
    
    return images