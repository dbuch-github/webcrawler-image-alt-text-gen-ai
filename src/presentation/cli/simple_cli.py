"""
Simple command-line interface for the WebCrawler
"""
import json
import argparse
import sys
from typing import Dict, Any

from ...core import scrape_url

def print_json(data: Dict[str, Any], pretty: bool = True) -> None:
    """Print data as formatted JSON"""
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False))

def run() -> None:
    """Run the simple CLI example"""
    parser = argparse.ArgumentParser(description='Web Crawler Example')
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--no-headless', action='store_true', help='Run with visible browser')
    parser.add_argument('--browser', choices=['auto', 'chrome', 'firefox'], default='auto', 
                        help='Browser to use (default: auto)')
    parser.add_argument('--json', action='store_true', help='Print raw JSON output')
    
    args = parser.parse_args()
    
    url = args.url
    headless = not args.no_headless
    browser = args.browser
    
    print(f"Scraping URL: {url}")
    print(f"Settings: headless={headless}, browser={browser}")
    print("-" * 50)
    
    # Get all data
    print("Scraping all data...")
    data = scrape_url(url, headless=headless, browser=browser)
    
    if args.json:
        print_json(data)
        return
    
    # Print title
    print("\nPage Title:")
    print(data.get('title', 'No title found'))
    
    # Print headlines
    print("\nHeadlines:")
    headlines = data.get('headlines', {})
    for tag, headings in headlines.items():
        if headings:
            print(f"\n{tag.upper()}:")
            for i, heading in enumerate(headings, 1):
                print(f"  {i}. {heading.get('text', heading)}")
    
    # Print images (limited to first 5)
    print("\nImages (first 5):")
    images = data.get('images', [])
    for i, img in enumerate(images[:5], 1):
        print(f"  {i}. URL: {img['url']}")
        if img.get('alt'):
            print(f"     Alt: {img['alt']}")
    
    if len(images) > 5:
        print(f"  ... and {len(images) - 5} more images")
    
    # Print part of the text content (first 500 chars)
    print("\nText Content Preview (first 500 chars):")
    text = data.get('text_content', '')
    print(text[:500] + ('...' if len(text) > 500 else ''))
    
    print("\nTotal scraped content:")
    print(f"- {len(headlines.get('h1', []))} h1 elements")
    print(f"- {len(headlines.get('h2', []))} h2 elements")
    print(f"- {len(headlines.get('h3', []))} h3 elements")
    print(f"- {len(images)} images")
    print(f"- {len(text)} characters of text")

if __name__ == "__main__":
    run()