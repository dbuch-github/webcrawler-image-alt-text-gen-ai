"""
WebCrawler Package

A flexible and powerful web crawler for extracting images and other content from websites.
"""

from .core import (
    WebCrawler, 
    scrape_url, 
    get_page_title, 
    get_headlines, 
    get_text_content, 
    get_images,
    Image,
    Headline, 
    WebPage
)

__all__ = [
    'WebCrawler',
    'scrape_url',
    'get_page_title',
    'get_headlines',
    'get_text_content',
    'get_images',
    'Image',
    'Headline',
    'WebPage'
]

__version__ = '1.0.0'