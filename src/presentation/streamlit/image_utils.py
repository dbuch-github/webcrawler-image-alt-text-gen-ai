"""
Image utility functions for the Streamlit interface
"""
import os
import tempfile
import requests
from PIL import Image
from typing import Dict, Any, Optional

import streamlit as st

def get_filesize(url: str) -> float:
    """
    Get the file size of an image in KB
    
    Args:
        url: URL of the image
        
    Returns:
        float: File size in KB
    """
    try:
        response = requests.head(url, timeout=5)
        if 'content-length' in response.headers:
            size_bytes = int(response.headers['content-length'])
            return round(size_bytes / 1024, 2)  # Convert to KB and round to 2 decimal places
        
        # If content-length header is not available, try to get the actual content
        response = requests.get(url, timeout=5, stream=True)
        size_bytes = len(response.content)
        return round(size_bytes / 1024, 2)
    except Exception as e:
        st.error(f"Error getting file size for {url}: {str(e)}")
        return 0.0

def get_image_as_thumbnail(url: str) -> Optional[Dict[str, Any]]:
    """
    Convert image URL to a thumbnail
    
    Args:
        url: URL of the image
        
    Returns:
        Dict with thumbnail info or None if there was an error
    """
    try:
        # Get content type from headers
        try:
            headers = requests.head(url, timeout=3).headers
            content_type = headers.get('content-type', '').lower()
        except:
            # If we can't get headers, try to guess from URL
            content_type = ''
        
        # Get file extension from URL
        file_ext = os.path.splitext(url.split('?')[0].lower())[1]
        
        # Check if it's an SVG image
        is_svg = file_ext == '.svg' or 'image/svg' in content_type
        
        # Check if it's a PNG image
        is_png = file_ext == '.png' or 'image/png' in content_type
        
        if is_svg:
            # For SVG images, we'll use a different approach
            # SVGs can be displayed directly in HTML
            return {
                'is_svg': True,
                'url': url
            }
        else:
            # For regular images (including PNG)
            # Use a session with proper headers to avoid issues with some servers
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': url
            })
            
            response = session.get(url, timeout=5, stream=True)
            
            # Check if we got a valid image
            if response.status_code != 200:
                raise Exception(f"Failed to download image: HTTP {response.status_code}")
                
            # For problematic images, save to a temporary file first and then open
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_download:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_download.write(chunk)
            
            # Now open the saved file
            try:
                img = Image.open(temp_download.name)
                
                # Create a thumbnail
                img.thumbnail((150, 150))
                
                # Save to a temporary file
                suffix = '.png'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_thumb:
                    img.save(temp_thumb, format='PNG')
                    
                    # Clean up the temporary download file
                    try:
                        os.unlink(temp_download.name)
                    except:
                        pass
                        
                    return {
                        'is_svg': False,
                        'is_png': is_png,
                        'path': temp_thumb.name
                    }
            except Exception as e:
                # Clean up the temporary download file
                try:
                    os.unlink(temp_download.name)
                except:
                    pass
                raise e
    except Exception as e:
        st.error(f"Error processing image {url}: {str(e)}")
        return None