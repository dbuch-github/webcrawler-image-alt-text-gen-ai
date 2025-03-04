"""
Test CLI for verifying that the WebCrawler is working correctly
"""
import sys
import platform
import logging
import argparse
from typing import Tuple

from ...core import scrape_url
from ...infrastructure import logger

def test_crawler() -> Tuple[bool, str]:
    """
    Run a basic test of the crawler functionality
    
    Returns:
        Tuple of (success, message)
    """
    logger.info("Web Crawler Test Script")
    logger.info("======================")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    logger.info("======================")
    
    logger.info("\nTesting crawler with example.com...")
    
    try:
        # Use Firefox directly since it's more reliable across platforms
        logger.info("Testing with Firefox browser...")
        result = scrape_url("https://example.com", browser="firefox")
        
        # Basic validation
        if result.get('title') == "Example Domain":
            return True, f"Test PASSED: Successfully scraped example.com\nTitle: {result['title']}\nH1 count: {len(result['headlines']['h1'])}"
        else:
            return False, f"Test FAILED: Unexpected title: {result.get('title', 'None')}"
            
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")
        return False, f"Test FAILED with exception: {str(e)}"

def run() -> None:
    """Run the test CLI"""
    parser = argparse.ArgumentParser(description='Web Crawler Test Script')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    success, message = test_crawler()
    
    # Print result
    if success:
        print(f"\n✅ {message}")
    else:
        print(f"\n❌ {message}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    run()