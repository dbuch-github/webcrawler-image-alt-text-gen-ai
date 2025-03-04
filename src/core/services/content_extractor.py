"""
Content extraction service for extracting text content and headlines
"""
import logging
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from ...core.models import Headline

logger = logging.getLogger(__name__)

class ContentExtractorService:
    """
    Service for extracting text content and headlines from web pages
    """
    
    def __init__(self, driver):
        """
        Initialize the content extractor service
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
    
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
                    
                    # Create headline object
                    headline = Headline(
                        text=element.text,
                        tag=tag,
                        id=element_id,
                        css_class=element.get_attribute('class'),
                        xpath=xpath,
                        url=current_url + (anchor if anchor else '')
                    )
                    
                    headlines[tag].append(headline)
        
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
            logger.error(f"Error extracting text content: {str(e)}")
            return ""