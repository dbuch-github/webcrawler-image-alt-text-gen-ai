# Advanced Python Web Crawler

A powerful web crawling and scraping tool built with Python, Selenium, and BeautifulSoup.

## Features

- Uses Selenium WebDriver for rendering JavaScript and handling dynamic content
- Mimics real browser behavior to prevent 403 errors
- Automatically handles GDPR/cookie consent banners in multiple languages
- Extracts useful content:
  - Page title
  - Headlines (H1, H2, H3)
  - Main text content
  - Images (URLs and alt text)
- Follows initial redirects
- Multi-browser support (Chrome and Firefox with auto-fallback)
- Optimized for different architectures (including Apple Silicon)

## Requirements

- Python 3.10 or higher
- Chrome and/or Firefox browser installed

**Note for Apple Silicon (M1/M2/M3) users:** Firefox is the recommended browser as there can be compatibility issues with Chrome on ARM architecture. The crawler will automatically try to use Firefox if Chrome fails.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/webcrawler.git
cd webcrawler
```

2. Create a conda environment:
```bash
conda create -n webcrawler python=3.10 -y
conda activate webcrawler
```

3. Install required packages:
```bash
conda install -c conda-forge selenium beautifulsoup4 requests webdriver-manager firefox geckodriver -y
```

4. Verify installation:
```bash
python test.py
```
You should see "Test PASSED" if everything is working correctly.

## Usage

### Basic Usage

```python
from crawler import scrape_url

# Get all data from a URL (default uses auto browser detection)
data = scrape_url("https://example.com")

# Specify browser explicitly
data = scrape_url("https://example.com", browser="firefox")

# Access specific data
print(data['title'])
print(data['headlines'])
print(data['text_content'])
print(data['images'])
```

### Individual Functions

```python
from crawler import get_page_title, get_headlines, get_text_content, get_images

# Get only the title
title = get_page_title("https://example.com")

# Get only the headlines (with Firefox)
headlines = get_headlines("https://example.com", browser="firefox")

# Get only the text content (with visible browser)
text = get_text_content("https://example.com", headless=False)

# Get only the images
images = get_images("https://example.com")
```

### Running the Example

The example.py script demonstrates how to use the crawler:

```bash
# Run in headless mode with auto browser detection (default)
python example.py https://example.com

# Run with visible browser
python example.py https://example.com --no-headless

# Specify browser
python example.py https://example.com --browser firefox

# Combine options
python example.py https://example.com --browser chrome --no-headless
```

## Web Crawler Class

For more advanced usage, you can use the WebCrawler class directly:

```python
from crawler import WebCrawler

# Initialize crawler with Firefox in headless mode
crawler = WebCrawler(headless=True, browser="firefox")

# Or use auto-detection with a visible browser
crawler = WebCrawler(headless=False, browser="auto")

# Load a page
crawler.load_page("https://example.com")

# Get data
title = crawler.get_page_title()
headlines = crawler.get_headlines()
text = crawler.get_text_content()
images = crawler.get_images()

# Don't forget the driver will be closed automatically when the crawler object is destroyed
# But you can explicitly close it if needed:
# crawler.driver.quit()
```

## Error Handling

The crawler includes robust error handling to deal with:

- Connection issues
- Timeouts
- Missing elements
- Browser initialization failures with automatic fallback

When using the convenience functions, errors are returned as dictionaries with an 'error' key or as error strings.

## License

MIT