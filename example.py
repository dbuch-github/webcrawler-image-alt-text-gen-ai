from crawler import scrape_url, get_page_title, get_headlines, get_text_content, get_images
import json
import sys
import argparse

def print_json(data):
    """Print data as formatted JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description='Web Crawler Example')
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--no-headless', action='store_true', help='Run with visible browser')
    parser.add_argument('--browser', choices=['auto', 'chrome', 'firefox'], default='auto', 
                        help='Browser to use (default: auto)')
    
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
                print(f"  {i}. {heading}")
    
    # Print images (limited to first 5)
    print("\nImages (first 5):")
    images = data.get('images', [])
    for i, img in enumerate(images[:5], 1):
        print(f"  {i}. URL: {img['url']}")
        if img['alt']:
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
    main()