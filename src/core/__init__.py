"""
Core functionality for the image crawler application.
This package contains the main business logic of the application.
"""

from .crawler import (
    WebCrawler, 
    scrape_url, 
    get_page_title, 
    get_headlines, 
    get_text_content, 
    get_images
)
from .models import Image, Headline, WebPage

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