"""
Advanced command-line interface for the WebCrawler with more options
"""
import json
import argparse
import time
from typing import Dict, Any, Optional

from ...core import WebCrawler

def print_json(data: Dict[str, Any], pretty: bool = True) -> None:
    """Print data as formatted JSON"""
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False))

def scrape_with_custom_logic(url: str, headless: bool = True, browser: str = 'auto', 
                            delay: int = 2, screenshot: bool = False) -> Optional[Dict[str, Any]]:
    """
    Demonstrate more complex scraping with custom handling
    
    Args:
        url: Website URL to scrape
        headless: Whether to run in headless mode
        browser: Browser to use
        delay: Delay in seconds after handling consent
        screenshot: Whether to take a screenshot
    """
    # Initialize crawler
    crawler = WebCrawler(headless=headless, browser=browser)
    
    print(f"Scraping {url} with custom logic...")
    
    # Load the page
    success = crawler.load_page(url)
    if not success:
        print(f"Failed to load {url}")
        return None
    
    # Take a screenshot if requested (before consent handling)
    if screenshot and not headless:
        print("Taking screenshot before consent handling...")
        screenshot_path = "before_consent.png"
        crawler.take_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
    
    # Wait for a moment after handling cookies
    if delay > 0:
        print(f"Waiting {delay} seconds for page to stabilize...")
        time.sleep(delay)
    
    # Take a screenshot if requested (after consent handling)
    if screenshot and not headless:
        print("Taking screenshot after consent handling...")
        screenshot_path = "after_consent.png"
        crawler.take_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
    
    # Get basic data
    title = crawler.get_page_title()
    print(f"\nPage title: {title}")
    
    # Get all headlines for analysis
    headlines = crawler.get_headlines()
    print("\nHeadlines structure:")
    for level, items in headlines.items():
        print(f"- {level}: {len(items)} items")
    
    # Print top headline of each type
    for level, items in headlines.items():
        if items:
            print(f"\nTop {level} headline: {items[0]}")
    
    # Get image count
    images = crawler.get_images()
    print(f"\nFound {len(images)} images")
    
    # Print first few images
    if images:
        print("\nSample images:")
        for i, img in enumerate(images[:3], 1):
            alt_text = img.get('alt', '') if img.get('alt', '') else '[No alt text]'
            print(f"{i}. {alt_text}: {img.get('url', '')[:100]}...")
    
    # Get text length for analysis
    text = crawler.get_text_content()
    word_count = len(text.split())
    print(f"\nApproximate word count: {word_count}")
    
    # Text summary (first sentence)
    first_sentence = text.split('.')[0] if text else ''
    print(f"\nFirst sentence: {first_sentence}")
    
    # Return structured data
    return {
        'url': url,
        'title': title,
        'headline_counts': {level: len(items) for level, items in headlines.items()},
        'image_count': len(images),
        'word_count': word_count,
        'first_sentence': first_sentence
    }

def run() -> None:
    """Run the advanced CLI example"""
    parser = argparse.ArgumentParser(description='Advanced Web Crawler Example')
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--no-headless', action='store_true', help='Run with visible browser')
    parser.add_argument('--browser', choices=['auto', 'chrome', 'firefox'], default='auto', 
                        help='Browser to use (default: auto)')
    parser.add_argument('--delay', type=int, default=2, help='Delay after cookie handling in seconds')
    parser.add_argument('--screenshot', action='store_true', help='Take screenshots (only works with --no-headless)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    results = scrape_with_custom_logic(
        args.url, 
        headless=not args.no_headless,
        browser=args.browser,
        delay=args.delay,
        screenshot=args.screenshot
    )
    
    if args.json and results:
        print("\nJSON Output:")
        print_json(results)

if __name__ == "__main__":
    run()