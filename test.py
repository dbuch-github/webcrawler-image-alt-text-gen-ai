#!/usr/bin/env python3
"""
Test script to verify that the web crawler is working correctly
"""

import sys
import platform
import logging
from crawler import scrape_url

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_crawler():
    """
    Run a basic test of the crawler functionality
    """
    print("Web Crawler Test Script")
    print("======================")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print("======================")
    
    print("\nTesting crawler with example.com...")
    
    try:
        # Use Firefox directly since it's more reliable across platforms
        logger.info("Testing with Firefox browser...")
        result = scrape_url("https://example.com", browser="firefox")
        
        # Basic validation
        if result.get('title') == "Example Domain":
            print("\n✅ Test PASSED: Successfully scraped example.com")
            print(f"Title: {result['title']}")
            print(f"H1 count: {len(result['headlines']['h1'])}")
            return True
        else:
            print(f"\n❌ Test FAILED: Unexpected title: {result.get('title', 'None')}")
            return False
            
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")
        print(f"\n❌ Test FAILED with exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_crawler()
    sys.exit(0 if success else 1)