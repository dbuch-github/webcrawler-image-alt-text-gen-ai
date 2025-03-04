"""
Image extraction service for finding and processing images from web pages
"""
import re
import logging
import requests
from typing import List, Set, Dict, Any
from urllib.parse import urlparse, urljoin
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from ...core.models import Image

logger = logging.getLogger(__name__)

class ImageExtractorService:
    """
    Service for extracting images from web pages using multiple techniques
    """
    
    def __init__(self, driver):
        """
        Initialize the image extractor service
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
    
    def get_images(self) -> List[Image]:
        """
        Extract all images from the page using multiple methods
        
        Returns:
            list: List of Image objects
        """
        images = []
        image_urls = set()  # To track unique URLs
        
        try:
            # Ensure the page is fully loaded with all dynamic content
            self._wait_for_network_idle()
            
            # Method 1: Find all <img> tags using Selenium
            self._extract_standard_images(images, image_urls)
            
            # Method 2: Find background images in style attributes
            self._extract_background_images(images, image_urls)
            
            # Method 3: Use BeautifulSoup for additional parsing
            self._extract_images_with_beautifulsoup(images, image_urls)
            
            # Method 4: Check for Shadow DOM content
            self._extract_shadow_dom_images(images, image_urls)
            
            # Method 5: Check for common image galleries
            self._extract_gallery_images(images, image_urls)
            
            # Method 6: Check for sliders and carousels
            self._extract_slider_images(images, image_urls)
            
            # Method 7: Check for dynamically generated content using JavaScript
            self._extract_javascript_images(images, image_urls)
            
            # Process and normalize URLs
            normalized_images = self._normalize_image_urls(images)
            
            # Deduplicate responsive images (same image in different sizes)
            deduplicated_images = self._deduplicate_responsive_images(normalized_images)
            
            # Add debug information about deduplication
            logger.info(f"Found {len(images)} total images, normalized to {len(normalized_images)}, deduplicated to {len(deduplicated_images)}")
            
            return deduplicated_images
            
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            return images
    
    def get_images_from_iframes(self) -> List[Image]:
        """
        Extract images from all iframes on the page
        
        Returns:
            list: List of Image objects from iframes
        """
        iframe_images = []
        
        try:
            # Find all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            if not iframes:
                return []
                
            logger.info(f"Found {len(iframes)} iframes to check for images")
            
            # Store the current window handle to return to later
            main_window = self.driver.current_window_handle
            
            for iframe in iframes:
                try:
                    # Get iframe src
                    iframe_src = iframe.get_attribute("src")
                    
                    if not iframe_src:
                        continue
                        
                    logger.info(f"Checking iframe with src: {iframe_src}")
                    
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
                            aria_label = img.get_attribute("aria-label") or ""
                            
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
                                    
                                    # Create Image object
                                    image = Image(
                                        url=url,
                                        alt=alt,
                                        title=title,
                                        aria_label=aria_label,
                                        type=f'iframe-{attr_name}',
                                        from_iframe=True,
                                        from_cdn=from_cdn,
                                        iframe_src=iframe_src
                                    )
                                    
                                    iframe_images.append(image)
                        except Exception as e:
                            logger.error(f"Error processing iframe image: {str(e)}")
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
                                            
                                            # Create Image object
                                            image = Image(
                                                url=bg_url,
                                                alt=element.get_attribute("alt") or element.get_attribute("title") or "",
                                                title=element.get_attribute("title") or "",
                                                aria_label=element.get_attribute("aria-label") or "",
                                                type='iframe-background',
                                                from_iframe=True,
                                                from_cdn=from_cdn,
                                                iframe_src=iframe_src
                                            )
                                            
                                            iframe_images.append(image)
                            except Exception as e:
                                logger.error(f"Error processing iframe background image: {str(e)}")
                                continue
                    except Exception as e:
                        logger.error(f"Error processing iframe background images: {str(e)}")
                    
                    # Switch back to the main content
                    self.driver.switch_to.default_content()
                except Exception as e:
                    logger.error(f"Error processing iframe: {str(e)}")
                    # Make sure we switch back to the main content even if there's an error
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
            
            logger.info(f"Found {len(iframe_images)} images in iframes")
            return iframe_images
            
        except Exception as e:
            logger.error(f"Error extracting images from iframes: {str(e)}")
            # Make sure we switch back to the main content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return []
    
    def _extract_standard_images(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract images from standard img tags"""
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
    
    def _extract_background_images(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract background images from style attributes"""
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
    
    def _extract_images_with_beautifulsoup(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract images using BeautifulSoup for more sophisticated parsing"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
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
            logger.error(f"Error in BeautifulSoup parsing: {str(e)}")
    
    def _extract_shadow_dom_images(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract images from Shadow DOM elements"""
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
            logger.error(f"Error checking Shadow DOM: {str(e)}")
    
    def _extract_gallery_images(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract images from common gallery elements"""
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
    
    def _extract_slider_images(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract images from slider and carousel elements"""
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
    
    def _extract_javascript_images(self, images: List[Dict[str, Any]], image_urls: Set[str]):
        """Extract images from JavaScript variables and objects"""
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
            logger.error(f"Error extracting JS images: {str(e)}")
    
    def _normalize_image_urls(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize image URLs and detect CDN domains"""
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
                    logger.info(f"Found image from different domain: {img_domain} (base: {base_domain})\nImage URL: {img['url']}\nEstimated size: {size_kb} KB")
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
                logger.error(f"Error normalizing URL {img.get('url', 'unknown')}: {str(e)}")
                # Keep the original URL if normalization fails
                normalized_images.append(img)
        
        return normalized_images
    
    def _deduplicate_responsive_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify and deduplicate responsive images (same image in different sizes)
        
        Args:
            images: List of image dictionaries
            
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
                logger.error(f"Error during image deduplication: {str(e)}")
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
    
    def _select_best_image(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best image from a group of similar images
        
        Args:
            images: List of similar image dictionaries
            
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
                        logger.info(f"Network idle detected after {time.time() - start_time:.2f} seconds")
                        return True
                        
                time.sleep(0.3)  # Poll every 300ms
                
            logger.warning(f"Network idle wait timed out after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Error waiting for network idle: {str(e)}")
            return False