"""
Streamlit web interface for the WebCrawler
"""
import os
import time
import pandas as pd
import streamlit as st

from ...core import WebCrawler
from .image_utils import get_filesize, get_image_as_thumbnail

def setup_streamlit_page():
    """Configure Streamlit page settings"""
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

def image_gallery(images):
    """Display images in an interactive gallery"""
    # Create a temporary column for thumbnails
    df = pd.DataFrame(images)
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
            
            # Show all relevant badges
            badges = []
            if row.get('from_cdn'):
                badges.append("🌐 CDN")
            if row.get('from_iframe'):
                badges.append("🖼️ iframe")
            if row.get('from_shadow_dom'):
                badges.append("🔒 Shadow DOM")
            if 'type' in row:
                if 'background' in row['type']:
                    badges.append("🎨 Background")
                if 'slider' in row['type'] or 'carousel' in row['type']:
                    badges.append("🔄 Slider")
                if 'js-' in row['type']:
                    badges.append("📜 JavaScript")
                if 'gallery' in row['type']:
                    badges.append("🖼️ Gallery")
            
            if badges:
                st.markdown(f"<div style='display:flex;gap:5px;margin-top:5px;flex-wrap:wrap;'>{' '.join([f'<span style=\"background-color:#e6f7ff;color:#1890ff;padding:2px 8px;border-radius:4px;font-size:12px;margin-bottom:3px;\">{badge}</span>' for badge in badges])}</div>", unsafe_allow_html=True)
        
        with col3:
            st.subheader("Alt Text")
            
            # Show alt text or aria-label if available
            if row.get('alt'):
                st.write(row['alt'])
            elif row.get('aria_label'):
                st.write(f"[aria-label] {row['aria_label']}")
            else:
                st.write("No alt text or aria-label")
                
            # Show image type for debugging
            if 'type' in row:
                st.markdown(f"<small style='color:#888;'>Type: {row['type']}</small>", unsafe_allow_html=True)
        
        with col4:
            st.subheader("Size")
            st.write(f"{row['size_kb']} KB")
        
        st.markdown("---")
    
    # Clean up temporary files
    for _, row in df.iterrows():
        try:
            # Handle the thumbnail format
            if row['thumbnail'] and isinstance(row['thumbnail'], dict) and not row['thumbnail'].get('is_svg'):
                if os.path.exists(row['thumbnail']['path']):
                    os.unlink(row['thumbnail']['path'])
            # Handle the old format for backward compatibility
            elif row['thumbnail'] and isinstance(row['thumbnail'], str) and os.path.exists(row['thumbnail']):
                os.unlink(row['thumbnail'])
        except Exception:
            # Silently ignore cleanup errors
            pass

def run():
    """Main function to run the Streamlit app"""
    # Clean up any screenshot files from previous runs
    if 'screenshot_files' in st.session_state:
        for file in st.session_state['screenshot_files']:
            try:
                if os.path.exists(file):
                    os.unlink(file)
            except Exception:
                # Silently ignore cleanup errors
                pass
        st.session_state['screenshot_files'] = []
    
    setup_streamlit_page()
    
    st.title("Webcrawler Image Analyzer")
    st.subheader("Analyze images from any website")
    
    # URL input and parameters
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url = st.text_input("Enter website URL:", placeholder="https://example.com")
    
    with col2:
        min_filesize = st.number_input("Minimum image size (KB):", min_value=0, value=0, step=5)
    
    # Advanced options in an expander
    with st.expander("Advanced Options"):
        headless = st.checkbox("Headless Mode", value=True, help="Run browser in background without UI")
        browser_option = st.selectbox("Browser", options=["auto", "chrome", "firefox"], index=0, help="Select which browser to use")
        consent_delay = st.slider("Consent Handling Delay (seconds)", min_value=1, max_value=10, value=2, help="Time to wait after handling consent dialogs")
        check_iframes = st.checkbox("Check iframes for images", value=True, help="Search for images within iframes")
        detect_cdn = st.checkbox("Enhanced CDN detection", value=True, help="Detect images from CDN domains and subdomains")
        enhanced_scrolling = st.checkbox("Enhanced scrolling", value=True, help="Use advanced scrolling techniques to find more lazy-loaded images")
        check_shadow_dom = st.checkbox("Check Shadow DOM", value=True, help="Look for images in Shadow DOM elements")
        min_wait_time = st.slider("Minimum wait time (seconds)", min_value=1, max_value=10, value=3, help="Minimum time to wait for page to load completely")
    
    # Add a scan button instead of automatically starting the crawler
    scan_button = st.button("Scan Images", type="primary", use_container_width=True)
    
    # Add a spinner during processing
    if url and scan_button:
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
                                # Create a clickable link that opens in a new tab
                                if isinstance(h, dict):
                                    st.markdown(f"<a href='{h['url']}' target='_blank'>{h['text']}</a>", unsafe_allow_html=True)
                                else:
                                    # Backward compatibility for old format
                                    st.write(h)
                        else:
                            st.info("No H1 headlines found")
                    
                    with tabs[1]:
                        if headlines['h2']:
                            for h in headlines['h2']:
                                # Create a clickable link that opens in a new tab
                                if isinstance(h, dict):
                                    st.markdown(f"<a href='{h['url']}' target='_blank'>{h['text']}</a>", unsafe_allow_html=True)
                                else:
                                    # Backward compatibility for old format
                                    st.write(h)
                        else:
                            st.info("No H2 headlines found")
                    
                    with tabs[2]:
                        if headlines['h3']:
                            for h in headlines['h3']:
                                # Create a clickable link that opens in a new tab
                                if isinstance(h, dict):
                                    st.markdown(f"<a href='{h['url']}' target='_blank'>{h['text']}</a>", unsafe_allow_html=True)
                                else:
                                    # Backward compatibility for old format
                                    st.write(h)
                        else:
                            st.info("No H3 headlines found")
                
                # Use the enhanced scrolling technique if selected
                if enhanced_scrolling:
                    # Use the improved scrolling method for better lazy-loading detection
                    crawler_instance._scroll_for_lazy_content()
                else:
                    # Use the basic scrolling method
                    crawler_instance.scroll_page()
                
                # Wait for the page to stabilize and load all content
                with st.spinner(f"Waiting {min_wait_time} seconds for all content to load..."):
                    time.sleep(min_wait_time)
                
                # Wait for network to be idle
                try:
                    crawler_instance._wait_for_network_idle(timeout=5, wait_time=1.0)
                except Exception as e:
                    st.warning(f"Network idle detection not available: {str(e)}")
                
                # Get images from main page
                images_data = crawler_instance.get_images()
                
                # Also check for images in iframes if selected
                if check_iframes:
                    iframe_images = crawler_instance.get_images_from_iframes()
                    if iframe_images:
                        images_data.extend(iframe_images)
            
            if not success:
                # Error already displayed above
                pass
            elif not images_data:
                st.error("No images found on the website")
            else:
                # Process images to add file size
                processed_images = []
                skipped_images = 0
                error_images = 0
                
                for img in images_data:
                    size_kb = get_filesize(img['url'])
                    img['size_kb'] = size_kb
                    
                    # Count errors
                    if size_kb == 0:
                        error_images += 1
                        
                    # Only add images that meet the minimum file size requirement
                    if size_kb >= min_filesize:
                        processed_images.append(img)
                    else:
                        skipped_images += 1
                
                # Clean up the crawler instance
                try:
                    del crawler_instance
                except:
                    pass
                
                if len(processed_images) == 0:
                    st.warning(f"No images found that meet the minimum size requirement of {min_filesize} KB")
                else:
                    # Display image count with detailed information
                    cdn_count = sum(1 for img in processed_images if img.get('from_cdn', False))
                    iframe_count = sum(1 for img in processed_images if img.get('from_iframe', False))
                    shadow_dom_count = sum(1 for img in processed_images if img.get('from_shadow_dom', False))
                    js_count = sum(1 for img in processed_images if img.get('type', '') and 'js-' in img.get('type', ''))
                    background_count = sum(1 for img in processed_images if img.get('type', '') and 'background' in img.get('type', ''))
                    slider_count = sum(1 for img in processed_images if img.get('type', '') and 'slider' in img.get('type', ''))
                    
                    # Show detailed summary
                    st.info(f"Found {len(processed_images)} images with size >= {min_filesize} KB")
                    
                    # Create a detailed summary expander
                    with st.expander("Detailed Image Summary"):
                        st.markdown(f"""
                        ### Image Detection Summary
                        - **Total images detected**: {len(images_data)}
                        - **Images meeting size criteria**: {len(processed_images)}
                        - **Images filtered out by size**: {skipped_images}
                        - **Images with size errors**: {error_images}
                        
                        > Note: The terminal debug log shows all detected images before size filtering.
                        """)
                    
                    # Create columns for the statistics
                    stat_cols = st.columns(3)
                    
                    with stat_cols[0]:
                        if cdn_count > 0:
                            st.success(f"✅ {cdn_count} images from CDN domains")
                        if iframe_count > 0:
                            st.success(f"✅ {iframe_count} images from iframes")
                    
                    with stat_cols[1]:
                        if shadow_dom_count > 0:
                            st.success(f"✅ {shadow_dom_count} images from Shadow DOM")
                        if js_count > 0:
                            st.success(f"✅ {js_count} images from JavaScript")
                    
                    with stat_cols[2]:
                        if background_count > 0:
                            st.success(f"✅ {background_count} background images")
                        if slider_count > 0:
                            st.success(f"✅ {slider_count} images from sliders/carousels")
                    
                    # Display images in a table
                    st.subheader("Images")
                    image_gallery(processed_images)

if __name__ == "__main__":
    run()