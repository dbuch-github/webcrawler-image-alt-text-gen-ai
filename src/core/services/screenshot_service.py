"""
Screenshot service for capturing webpage screenshots
"""
import os
import time
import tempfile
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class ScreenshotService:
    """
    Service for capturing screenshots of web pages
    """
    
    def __init__(self, driver):
        """
        Initialize the screenshot service
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
    
    def take_screenshot(self, output_path: Optional[str] = None, 
                        resolution: Tuple[int, int] = (1920, 1080)) -> Optional[str]:
        """
        Take a screenshot of the current page with specified browser window size
        
        Args:
            output_path (str, optional): Path to save the screenshot. If None, a temporary file is created.
            resolution (tuple): Browser window size in pixels as (width, height)
            
        Returns:
            str: Path to the screenshot file, or None if there was an error
        """
        try:
            if output_path is None:
                # Create a temporary file with .png extension
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                output_path = temp_file.name
                temp_file.close()
            
            # Store original window size
            original_size = self.driver.get_window_size()
            
            # Set window size to specified resolution
            self.driver.set_window_size(resolution[0], resolution[1])
            
            # Wait a moment for the page to adjust to the new size
            time.sleep(0.5)
            
            # Take screenshot
            self.driver.save_screenshot(output_path)
            
            # Restore original window size
            self.driver.set_window_size(original_size['width'], original_size['height'])
            
            return output_path
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            
            # Clean up if there was an error and we created a temporary file
            if output_path and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
                    
            return None