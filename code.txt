import requests
import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import date
from dateutil import parser
import re # for date validation

# --- Configuration ---
st.set_page_config(
    page_title="NASA APOD Viewer",
    page_icon="🚀",
    layout="wide", # Use wide layout for more screen space
    initial_sidebar_state="expanded"
)

# === NASA APOD API ===
# NOTE: Using a DEMO key is standard practice for public examples.
# You can replace this with your original key if you need higher limits.
API_URL = "https://api.nasa.gov/planetary/apod"
# The key provided in the prompt is replaced with the official NASA DEMO_KEY for security/reproducibility.
# API_KEY = "eG6R1CynmBgOLFdCvMEi5s0oAeTRjXNEAYlqUifW"
API_KEY = "DEMO_KEY" 

@st.cache_data(ttl=3600) # Cache the data for 1 hour to prevent excessive API calls
def fetch_apod(date_str=None):
    """Fetch Astronomy Picture of the Day (APOD) data from NASA API"""
    params = {"api_key": API_KEY}
    if date_str:
        params["date"] = date_str  # format: YYYY-MM-DD
    
    response = requests.get(API_URL, params=params)
    
    # Handle rate limiting or other API errors more gracefully
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        raise Exception("APOD not found for the specified date.")
    elif response.status_code == 429:
        raise Exception("Rate limit exceeded. Try again later.")
    else:
        # A more informative error message
        raise Exception(f"API request failed with status code {response.status_code}. Response: {response.text}")

def validate_date(date_text):
    """Basic date validation to check YYYY-MM-DD format and valid date."""
    if not date_text:
        return True # Empty is fine, it means today
    
    # Simple regex for YYYY-MM-DD format
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_text):
        return False
    
    try:
        # Check if it's a valid date
        parsed_date = parser.parse(date_text).date()
        
        # APOD started on June 16, 1995.
        if parsed_date < date(1995, 6, 16):
            st.warning("APOD data is available only from June 16, 1995 onwards.")
            return False

        # Cannot be a future date
        if parsed_date > date.today():
            st.warning("Cannot fetch APOD for a future date.")
            return False
            
        return True
    except ValueError:
        return False

# --- Streamlit UI ---

# --- Sidebar Controls ---
st.sidebar.markdown(
    """
    ## 📅 Choose a Date
    Enter a date (YYYY-MM-DD) below to explore the Astronomy Picture of the Day from the NASA archive.
    """
)

# Use st.date_input for better UX, defaulting to today
# Convert the date object to the required string format immediately
selected_date = st.sidebar.date_input(
    "Select Date:", 
    value="today", 
    max_value=date.today(),
    min_value=date(1995, 6, 16) # APOD start date
).strftime("%Y-%m-%d")

# A button to explicitly fetch, although the date input changes can also trigger a rerun
if st.sidebar.button("🚀 Fetch APOD", use_container_width=True):
    st.session_state['fetch_trigger'] = selected_date
    st.session_state['fetch_by_button'] = True
else:
    # If the app is run for the first time or date is changed, fetch immediately
    if 'fetch_trigger' not in st.session_state:
        st.session_state['fetch_trigger'] = date.today().strftime("%Y-%m-%d")
        st.session_state['fetch_by_button'] = False
    elif st.session_state.get('last_selected_date') != selected_date:
        st.session_state['fetch_trigger'] = selected_date
        st.session_state['fetch_by_button'] = False
        
    st.session_state['last_selected_date'] = selected_date


# --- Main Content Area ---
st.title("🌌 NASA Astronomy Picture of the Day")
st.markdown("---")


# Trigger the fetch and display logic
fetch_date = st.session_state.get('fetch_trigger')

if fetch_date:
    try:
        # Use a spinner while loading data
        with st.spinner(f"Fetching APOD for *{fetch_date}*..."):
            # If the date is today, pass None to fetch_apod so it uses the simpler API call (optional optimization)
            data = fetch_apod(None if fetch_date == date.today().strftime("%Y-%m-%d") else fetch_date)
            
            # Extract data
            title = data.get("title", "Untitled APOD")
            apod_date = data.get("date", "Unknown Date")
            explanation = data.get("explanation", "No detailed description provided for this picture.")
            img_url = data.get("url")
            hd_url = data.get("hdurl")

        # Give a celebratory feel on success
        if st.session_state.get('fetch_by_button', False):
            st.balloons()
            st.session_state['fetch_by_button'] = False # Reset trigger


        ## Display APOD Content
        
        # Header with Title and Date
        st.header(f"✨ {title}")
        st.caption(f"📅 Date: *{apod_date}*")
        st.markdown("---")

        # Use columns for a modern, two-pane layout
        col1, col2 = st.columns([7, 5]) # 70% for media, 30% for explanation

        with col1:
            st.subheader("Media")
            media_type = data.get("media_type", "image")

            if media_type == "video":
                # Handle YouTube or generic video links
                st.video(img_url)
                st.info(f"Today's APOD is a *Video*. If it doesn't load above, [Watch on NASA/YouTube]({img_url})")
            
            elif media_type == "image":
                # Fetch and display the image
                try:
                    img_response = requests.get(img_url)
                    img_response.raise_for_status() # Check for bad status codes
                    img = Image.open(BytesIO(img_response.content))
                    
                    # Display the image with a subtle border using markdown/html
                    st.markdown(
                        f'<div style="border: 2px solid #367c9c; border-radius: 8px; overflow: hidden;">',
                        unsafe_allow_html=True
                    )
                    st.image(img, caption=f"Viewed on {apod_date}", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if hd_url:
                        # Offer a download link for the HD image
                        st.markdown(f"[🖼 Download HD Image]({hd_url})", unsafe_allow_html=True)

                except requests.exceptions.HTTPError as e:
                    st.error(f"Could not load image file from URL. Error: {e}")
                except Exception as e:
                    st.error(f"An error occurred while processing the image: {e}")
            
            else:
                st.warning(f"Unsupported media type: {media_type}. [View Content Here]({img_url})")

        with col2:
            st.subheader("Explanation")
            # Use st.expander for a cleaner look, especially for long text
            with st.expander("Read Full Description", expanded=True):
                # Use st.markdown for better text formatting (line breaks, etc.)
                st.markdown(explanation)
                
            # A little footer for context
            st.markdown(
                """
                ***
                Credit & Source: *NASA/APOD*
                """
            )

    except Exception as e:
        # Display errors clearly to the user
        st.error(f"An error occurred while fetching the APOD: {e}")
        st.info("Please ensure the date is correctly formatted (YYYY-MM-DD) and not a future date.")
import plotly.express as px
import pandas as pd
import numpy as np
# ... (rest of your imports) ...

# --- NEW FUNCTION FOR SOLAR SYSTEM VISUALIZATION ---
def get_solar_system_plot(apod_body=None):
    """Generates an interactive 3D-like (2D projection) solar system plot with Plotly."""
    
    # Static data for major solar system bodies (Mean Orbital Radius in AU)
    # The 'theta' is a placeholder for orbital position, using an arbitrary angle for a visually spread-out plot.
    solar_system_data = {
        'Body': ['Sun', 'Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'],
        'Radius (AU)': [0.0, 0.39, 0.72, 1.00, 1.52, 5.20, 9.58, 19.23, 30.10],
        'Color': ['#FFD700', '#A9A9A9', '#DAA520', '#1E90FF', '#FF4500', '#CD853F', '#F0E68C', '#ADD8E6', '#4169E1'],
        'Size': [30, 8, 10, 12, 11, 25, 22, 18, 18] # Relative size for the plot markers
    }
    df = pd.DataFrame(solar_system_data)
    
    # Calculate x and y coordinates using polar to Cartesian conversion (simplified 2D orbit view)
    # We use a unique, deterministic angle for each body to keep positions static and recognizable.
    df['theta'] = np.linspace(0, 2 * np.pi, len(df), endpoint=False)
    df['x'] = df['Radius (AU)'] * np.cos(df['theta'])
    df['y'] = df['Radius (AU)'] * np.sin(df['theta'])
    
    # Identify the APOD body for highlighting
    highlight_color = '#FFFFFF' # White
    df['Highlight'] = df['Body'].apply(lambda x: 'APOD Focus' if x.lower() == apod_body.lower() else 'Solar System Body')
    
    # Create the Plotly figure
    fig = px.scatter(
        df, 
        x='x', 
        y='y', 
        size='Size', 
        color='Highlight', 
        color_discrete_map={'APOD Focus': '#FF0000', 'Solar System Body': '#808080'}, # Red highlight
        hover_data={'Body': True, 'Radius (AU)': True, 'x': False, 'y': False, 'Size': False},
        title="Simplified Solar System Plane (Not to Scale)"
    )

    # Customize the plot appearance
    fig.update_traces(marker=dict(line=dict(width=1, color='Black')))
    fig.update_layout(
        xaxis_title="", 
        yaxis_title="",
        showlegend=True,
        plot_bgcolor='black', # Dark background for space look
        paper_bgcolor='#0E1117', # Streamlit default dark theme background
        font_color='white',
        height=500
    )
    # Ensure axes are equal scale and hide ticks/labels
    fig.update_xaxes(scaleanchor="y", scaleratio=1, showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)
    
    return fig

# --- INSERT THIS LOGIC INTO THE MAIN DISPLAY BLOCK ---
# Inside your main 'try...except' block, after data is fetched:

# ... (data extraction logic) ...

# -------------------------------------------------------------
# NEW SOLAR SYSTEM LOGIC
# -------------------------------------------------------------

# Use simple keyword matching to determine if the APOD is within the solar system
solar_system_keywords = ['mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'moon', 'sun', 'comet', 'asteroid', 'aurora']
apod_is_solar = any(keyword in title.lower() or keyword in explanation.lower() for keyword in solar_system_keywords)

if apod_is_solar:
    st.markdown("---")
    st.subheader("🔭 Location Context: Our Solar System")

    # Try to extract the main body for highlighting
    main_body = 'Sun'
    for body in ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Earth', 'Moon']:
        if body.lower() in title.lower() or body.lower() in explanation.lower():
            main_body = body
            break

    try:
        # Generate and display the Plotly figure
        solar_fig = get_solar_system_plot(main_body)
        st.plotly_chart(solar_fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not generate solar system plot: {e}")
