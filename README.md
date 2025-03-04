# WebCrawler Image Analyzer

A powerful web crawling and scraping tool built with Python, Selenium, and BeautifulSoup, designed to thoroughly analyze images and their accessibility information on websites.

## Features

- **Comprehensive Image Detection**: Finds images from multiple sources:
  - Standard img tags
  - CSS backgrounds
  - Shadow DOM elements
  - iframes content
  - JavaScript variables
  - Responsive images (srcset)
  - Lazy-loaded images
  - Gallery and slider components
- **Advanced Consent Handling**: Automatically detects and accepts cookie/GDPR consent banners in multiple languages
- **Enhanced Lazy Loading**: Uses multiple scrolling techniques to trigger lazy-loaded content
- **Multiple Interfaces**: Command line, Streamlit web UI
- **Browser Support**: Chrome and Firefox with auto-fallback
- **Rich Content Extraction**: Headlines, text content, and images with detailed metadata
- **Accessibility Analysis**: Evaluates image alt text presence and quality

## Architecture

This application follows a modular, layered architecture:

```
src/
├── core/                # Core business logic layer
│   ├── models.py        # Domain models
│   ├── services/        # Service components
│   └── crawler.py       # Main crawler implementation
├── infrastructure/      # Infrastructure layer
│   ├── config.py        # Application configuration
│   ├── logging_config.py # Logging setup
│   └── webdriver_factory.py # Browser selection & setup
└── presentation/        # Presentation layer
    ├── cli/             # Command-line interfaces
    └── streamlit/       # Streamlit web UI
```

### Design Patterns Used

- **Factory Pattern**: For WebDriver creation and configuration
- **Dependency Injection**: Services are injected into the crawler
- **Strategy Pattern**: Different strategies for image extraction
- **Repository Pattern**: For handling image collections
- **Facade Pattern**: Simple API for complex operations

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
pip install -r requirements.txt
```

4. Verify installation:
```bash
python test.py
```
You should see "Test PASSED" if everything is working correctly.

## Usage

### Command-Line Interface

#### Simple Example

```bash
python example.py https://example.com
```

Options:
- `--no-headless`: Run with visible browser
- `--browser {auto,chrome,firefox}`: Specify browser to use
- `--json`: Output raw JSON data

#### Advanced Example

```bash
python complex_example.py https://example.com --no-headless --browser firefox --delay 3 --screenshot --json
```

Additional options:
- `--delay SECONDS`: Wait time after handling consent banners
- `--screenshot`: Take screenshots before and after consent handling (only works with `--no-headless`)

#### Testing

```bash
python test.py --verbose
```

### Streamlit Web Interface

```bash
streamlit run app.py
```

The Streamlit interface provides a user-friendly way to:
- Enter URLs to crawl
- Configure crawler settings
- View extracted images with thumbnails
- Analyze image metadata (alt text, size, URL)
- Filter images by size
- View detected image sources (CDN, iframe, Shadow DOM, etc.)

### API Usage

```python
from src import WebCrawler, scrape_url, get_images

# Simple usage
images = get_images("https://example.com")

# More control
crawler = WebCrawler(headless=True, browser="chrome")
crawler.load_page("https://example.com")
headlines = crawler.get_headlines()
text = crawler.get_text_content()
images = crawler.get_images()
```

## Key Components

- **WebDriverFactory**: Creates and configures browser instances with appropriate settings
- **PageLoaderService**: Handles page loading, consent banners, and scrolling
- **ContentExtractorService**: Extracts text content and headlines
- **ImageExtractorService**: Comprehensive image detection and processing
- **ScreenshotService**: Captures page screenshots for verification and debugging

## Error Handling

The crawler includes robust error handling to deal with:

- Connection issues
- Timeouts
- Missing elements
- Browser initialization failures with automatic fallback

When using the convenience functions, errors are returned as dictionaries with an 'error' key or as error strings.

## License

MIT