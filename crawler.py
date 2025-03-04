import time
import platform
import logging
import tempfile
import re
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
        Extract all images from the page using multiple methods
        
        Returns:
            list: List of dictionaries with image information (url, alt text)
        """
        images = []
        image_urls = set()  # To track unique URLs
        
        try:
            # Method 1: Find all <img> tags using Selenium
            elements = self.driver.find_elements(By.TAG_NAME, "img")
            
            for element in elements:
                try:
                    # Try different attributes where image URLs might be stored
                    src = element.get_attribute("src")
                    data_src = element.get_attribute("data-src")
                    data_lazy_src = element.get_attribute("data-lazy-src")
                    srcset = element.get_attribute("srcset")
                    
                    # Get alt text and other metadata
                    alt = element.get_attribute("alt") or ""
                    title = element.get_attribute("title") or ""
                    
                    # Process the main source if available
                    if src and src not in image_urls and not src.startswith("data:"):
                        image_urls.add(src)
                        images.append({
                            'url': src,
                            'alt': alt,
                            'title': title,
                            'type': 'img'
                        })
                    
                    # Process data-src (lazy loading)
                    if data_src and data_src not in image_urls and not data_src.startswith("data:"):
                        image_urls.add(data_src)
                        images.append({
                            'url': data_src,
                            'alt': alt,
                            'title': title,
                            'type': 'img-lazy'
                        })
                    
                    # Process data-lazy-src (another lazy loading variant)
                    if data_lazy_src and data_lazy_src not in image_urls and not data_lazy_src.startswith("data:"):
                        image_urls.add(data_lazy_src)
                        images.append({
                            'url': data_lazy_src,
                            'alt': alt,
                            'title': title,
                            'type': 'img-lazy'
                        })
                    
                    # Process srcset (responsive images)
                    if srcset:
                        try:
                            # Parse srcset attribute which can contain multiple URLs
                            srcset_parts = srcset.split(',')
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
                                            'type': 'srcset'
                                        })
                        except:
                            pass  # Skip if srcset parsing fails
                except:
                    continue
            
            # Method 2: Find background images in style attributes
            try:
                # Find elements with background-image style
                elements_with_bg = self.driver.find_elements(By.XPATH, "//*[contains(@style, 'background-image')]")
                
                for element in elements_with_bg:
                    try:
                        style = element.get_attribute("style")
                        if style and 'url(' in style:
                            # Extract URL from background-image: url('...')
                            bg_url_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                            if bg_url_match:
                                bg_url = bg_url_match.group(1)
                                if bg_url and bg_url not in image_urls and not bg_url.startswith("data:"):
                                    image_urls.add(bg_url)
                                    images.append({
                                        'url': bg_url,
                                        'alt': element.get_attribute("alt") or element.get_attribute("title") or "",
                                        'title': element.get_attribute("title") or "",
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
                                        images.append({
                                            'url': srcset_url,
                                            'alt': source.get('alt', ''),
                                            'title': source.get('title', ''),
                                            'type': 'picture-source'
                                        })
                
                # Find CSS with background images
                style_tags = soup.find_all('style')
                for style_tag in style_tags:
                    style_content = style_tag.string
                    if style_content:
                        # Find all background-image: url(...) patterns
                        bg_urls = re.findall(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style_content)
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
                
            # Method 4: Check for common image galleries
            try:
                # Look for data-attributes commonly used in galleries
                gallery_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//*[contains(@class, 'gallery') or contains(@id, 'gallery') or contains(@data-gallery, 'true')]"
                )
                
                for gallery in gallery_elements:
                    # Find all elements with data-src, data-full, data-image attributes
                    data_elements = gallery.find_elements(
                        By.XPATH, 
                        ".//*[@data-src or @data-full or @data-image or @data-lazy or @data-thumb]"
                    )
                    
                    for element in data_elements:
                        try:
                            # Check various data attributes for image URLs
                            for attr in ['data-src', 'data-full', 'data-image', 'data-lazy', 'data-thumb']:
                                url = element.get_attribute(attr)
                                if url and url not in image_urls and not url.startswith("data:"):
                                    image_urls.add(url)
                                    images.append({
                                        'url': url,
                                        'alt': element.get_attribute("alt") or element.get_attribute("title") or "",
                                        'title': element.get_attribute("title") or "",
                                        'type': f'gallery-{attr}'
                                    })
                        except:
                            continue
            except:
                pass  # Skip if gallery extraction fails
            
            # Process and normalize URLs
            normalized_images = []
            base_url = self.driver.current_url
            
            for img in images:
                try:
                    # Handle relative URLs
                    if img['url'].startswith('//'):  # Protocol-relative URL
                        img['url'] = 'https:' + img['url']
                    elif img['url'].startswith('/'):  # Root-relative URL
                        parsed_base = urlparse(base_url)
                        img['url'] = f"{parsed_base.scheme}://{parsed_base.netloc}{img['url']}"
                    elif not img['url'].startswith(('http://', 'https://')):  # Relative URL
                        img['url'] = urljoin(base_url, img['url'])
                    
                    normalized_images.append(img)
                except:
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
                
                # Create a group key based on the path and alt text
                # This helps group images that are the same but have different sizes
                group_key = f"{parsed_url.netloc}{path_signature}_{alt_text}"
                
                if group_key not in image_groups:
                    image_groups[group_key] = []
                    
                image_groups[group_key].append(img)
            except:
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
        Take a screenshot of the current page
        
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
            
            # Take screenshot
            self.driver.save_screenshot(output_path)
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
    
    return crawler.get_images()