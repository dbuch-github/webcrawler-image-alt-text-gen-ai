import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import crawler
import pandas as pd
import time
import os
import tempfile
from crawler import WebCrawler

st.set_page_config(
    page_title="Webcrawler Image Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stDataFrame {
        width: 100%;
    }
    .image-thumbnail {
        max-width: 150px;
        max-height: 150px;
    }
    h1, h2, h3 {
        color: #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

def get_filesize(url):
    """Get the file size of an image in KB"""
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
        return 0

def get_image_as_thumbnail(url):
    """Convert image URL to a thumbnail"""
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

def main():
    st.title("Webcrawler Image Analyzer")
    st.subheader("Analyze images from any website")
    
    # URL input and parameters
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url = st.text_input("Enter website URL:", placeholder="https://example.com")
    
    with col2:
        min_filesize = st.number_input("Minimum image size (KB):", min_value=0, value=10, step=5)
    
    # Advanced options in an expander
    with st.expander("Advanced Options"):
        headless = st.checkbox("Headless Mode", value=True, help="Run browser in background without UI")
        browser_option = st.selectbox("Browser", options=["auto", "chrome", "firefox"], index=0, help="Select which browser to use")
        consent_delay = st.slider("Consent Handling Delay (seconds)", min_value=1, max_value=10, value=2, help="Time to wait after handling consent dialogs")
    
    # Add a spinner during processing
    if url:
        with st.spinner("Crawling website and analyzing images..."):
            # Initialize the crawler directly for more control
            crawler_instance = WebCrawler(headless=headless, browser=browser_option)
            
            # Load the page with consent handling
            st.info(f"Loading {url} and handling consent dialogs...")
            success = crawler_instance.load_page(url)
            
            if not success:
                st.error(f"Failed to load {url}")
            else:
                # Wait for the specified delay after consent handling
                with st.spinner(f"Waiting {consent_delay} seconds for page to stabilize after consent handling..."):
                    time.sleep(consent_delay)
                    
                    # Try to handle consent again after waiting (some sites have multiple layers)
                    crawler_instance._handle_consent_banners()
                    # Wait a bit more after the second consent handling attempt
                    time.sleep(1)
                
                # Get page title
                title = crawler_instance.get_page_title()
                st.header(f"Website: {title}")
                
                # Take a screenshot of the page after consent handling and delay
                screenshot_path = crawler_instance.take_screenshot()
                if screenshot_path:
                    st.image(screenshot_path, caption="Website Screenshot (after consent handling)", use_container_width=True)
                    
                    # Store screenshot path for cleanup
                    if 'screenshot_files' not in st.session_state:
                        st.session_state['screenshot_files'] = []
                    st.session_state['screenshot_files'].append(screenshot_path)
                else:
                    st.error("Failed to capture website screenshot")
                
                # Get headlines
                headlines = crawler_instance.get_headlines()
                
                if not headlines:
                    st.error("Error fetching headlines")
                else:
                    # Display headlines
                    st.subheader("Headlines")
                    tabs = st.tabs(["H1", "H2", "H3"])
                    
                    with tabs[0]:
                        if headlines['h1']:
                            for h in headlines['h1']:
                                st.markdown(f"### {h}")
                        else:
                            st.info("No H1 headlines found")
                    
                    with tabs[1]:
                        if headlines['h2']:
                            for h in headlines['h2']:
                                st.markdown(f"## {h}")
                        else:
                            st.info("No H2 headlines found")
                    
                    with tabs[2]:
                        if headlines['h3']:
                            for h in headlines['h3']:
                                st.markdown(f"# {h}")
                        else:
                            st.info("No H3 headlines found")
                
                # Get images
                images_data = crawler_instance.get_images()
            
            if not success:
                # Error already displayed above
                pass
            elif not images_data:
                st.error("No images found on the website")
            else:
                # Process images to add file size
                processed_images = []
                
                for img in images_data:
                    size_kb = get_filesize(img['url'])
                    img['size_kb'] = size_kb
                    # Only add images that meet the minimum file size requirement
                    if size_kb >= min_filesize:
                        processed_images.append(img)
                
                # Create DataFrame
                df = pd.DataFrame(processed_images)
                
                # Clean up the crawler instance
                try:
                    crawler_instance.driver.quit()
                except:
                    pass
                
                if df.empty:
                    st.warning(f"No images found that meet the minimum size requirement of {min_filesize} KB")
                else:
                    # Display image count
                    st.info(f"Found {len(df)} images with size >= {min_filesize} KB (filtered from {len(images_data)} total images)")
                    
                    # Display images in a table
                    st.subheader("Images")
                    
                    # Create a temporary column for thumbnails
                    df['thumbnail'] = df['url'].apply(get_image_as_thumbnail)
                    
                    # Create a custom dataframe display
                    for i, row in df.iterrows():
                        col1, col2, col3, col4 = st.columns([1, 3, 3, 1])
                        
                        with col1:
                            if row['thumbnail']:
                                if isinstance(row['thumbnail'], dict) and row['thumbnail'].get('is_svg'):
                                    # For SVG images, use HTML to display them
                                    st.markdown(f'''
                                    <div style="width:150px; height:150px; display:flex; align-items:center; justify-content:center;">
                                        <img src="{row['thumbnail']['url']}" style="max-width:150px; max-height:150px;">
                                    </div>
                                    ''', unsafe_allow_html=True)
                                elif isinstance(row['thumbnail'], dict) and row['thumbnail'].get('is_png'):
                                    # For PNG images, use the path directly
                                    st.image(row['thumbnail']['path'], width=150, caption="PNG")
                                elif isinstance(row['thumbnail'], dict) and not row['thumbnail'].get('is_svg'):
                                    # For other regular images with the new format
                                    st.image(row['thumbnail']['path'], width=150)
                                else:
                                    # For backward compatibility
                                    st.image(row['thumbnail'], width=150)
                            else:
                                st.write("Image not available")
                        
                        with col2:
                            st.subheader("URL")
                            st.write(row['url'])
                        
                        with col3:
                            st.subheader("Alt Text")
                            st.write(row['alt'] if row['alt'] else "No alt text")
                        
                        with col4:
                            st.subheader("Size")
                            st.write(f"{row['size_kb']} KB")
                        
                        st.markdown("---")
                    
                    # Clean up temporary files
                    for _, row in df.iterrows():
                        try:
                            # Handle the new thumbnail format
                            if row['thumbnail'] and isinstance(row['thumbnail'], dict) and not row['thumbnail'].get('is_svg'):
                                if os.path.exists(row['thumbnail']['path']):
                                    os.unlink(row['thumbnail']['path'])
                            # Handle the old format for backward compatibility
                            elif row['thumbnail'] and isinstance(row['thumbnail'], str) and os.path.exists(row['thumbnail']):
                                os.unlink(row['thumbnail'])
                        except Exception as e:
                            # Silently ignore cleanup errors
                            pass

if __name__ == "__main__":
    # Clean up any screenshot files from previous runs
    if 'screenshot_files' in st.session_state:
        for file in st.session_state['screenshot_files']:
            try:
                if os.path.exists(file):
                    os.unlink(file)
            except Exception as e:
                # Silently ignore cleanup errors
                pass
        st.session_state['screenshot_files'] = []
    
    main()
