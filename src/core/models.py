"""
Domain models for the webcrawler application
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse

@dataclass
class Headline:
    """
    Represents a headline element from a webpage
    """
    text: str
    tag: str  # h1, h2, h3, etc.
    id: Optional[str] = None
    css_class: Optional[str] = None
    xpath: Optional[str] = None
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'text': self.text,
            'id': self.id,
            'class': self.css_class,
            'xpath': self.xpath,
            'url': self.url
        }

@dataclass
class Image:
    """
    Represents an image found on a webpage
    """
    url: str
    alt: str = ""
    title: str = ""
    aria_label: str = ""
    type: str = "img"  # img, background, srcset, etc.
    from_cdn: bool = False
    from_iframe: bool = False
    from_shadow_dom: bool = False
    iframe_src: Optional[str] = None
    size_kb: float = 0.0
    
    def __post_init__(self):
        """Automatically determine if from CDN based on URL"""
        if not self.from_cdn and self.url and '://' in self.url:
            parsed_url = urlparse(self.url)
            self.from_cdn = 'cdn' in parsed_url.netloc or 'img' in parsed_url.netloc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'url': self.url,
            'alt': self.alt,
            'title': self.title,
            'aria_label': self.aria_label,
            'type': self.type,
            'from_cdn': self.from_cdn,
            'from_iframe': self.from_iframe,
            'from_shadow_dom': self.from_shadow_dom,
            'iframe_src': self.iframe_src,
            'size_kb': self.size_kb
        }

@dataclass
class WebPage:
    """
    Represents a crawled webpage with all its extracted content
    """
    url: str
    title: str = ""
    headlines: Dict[str, List[Headline]] = field(default_factory=lambda: {
        'h1': [], 'h2': [], 'h3': []
    })
    images: List[Image] = field(default_factory=list)
    text_content: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'url': self.url,
            'title': self.title,
            'headlines': {
                tag: [h.to_dict() for h in headings] 
                for tag, headings in self.headlines.items()
            },
            'images': [img.to_dict() for img in self.images],
            'text_content': self.text_content
        }