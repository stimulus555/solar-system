import requests
import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import date
import re
import plotly.express as px
import pandas as pd
import numpy as np

# --- Configuration ---
# Set page configuration for a modern, wide layout
st.set_page_config(
    page_title="NASA APOD Viewer",
    page_icon="🚀",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# === NASA APOD API ===
API_URL = "https://api.nasa.gov/planetary/apod"
# NOTE: Using NASA's official DEMO_KEY for reproducibility and security.
API_KEY = "DEMO_KEY" 

@st.cache_data(ttl=3600) # Cache the data for 1 hour to prevent excessive API calls
def fetch_apod(date_str=None):
    """Fetch Astronomy Picture of the Day (APOD) data from NASA API"""
    params = {"api_key": API_KEY}
    if date_str:
        params["date"] = date_str  # format: YYYY-MM-DD
    
    response = requests.get(API_URL, params=params)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 429:
        raise Exception("Rate limit exceeded. Please try again later.")
    else:
        raise Exception(f"API request failed with status code {response.status_code}. Response: {response.text}")

# --- FUNCTION FOR SOLAR SYSTEM VISUALIZATION (Plotly) ---
def get_solar_system_plot(apod_body=None):
    """Generates an interactive 2D projection solar system plot with Plotly."""
    
    # Static data for major solar system bodies (Mean Orbital Radius in AU)
    solar_system_data = {
        'Body': ['Sun', 'Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'],
        'Radius (AU)': [0.0, 0.39, 0.72, 1.00, 1.52, 5.20, 9.58, 19.23, 30.10],
        'Size': [30, 8, 10, 12, 11, 25, 22, 18, 18]
    }
    df = pd.DataFrame(solar_system_data)
    
    # Calculate x and y coordinates (simplified 2D orbit view)
    df['theta'] = np.linspace(0, 2 * np.pi, len(df), endpoint=False)
    df['x'] = df['Radius (AU)'] * np.cos(df['theta'])
    df['y'] = df['Radius (AU)'] * np.sin(df['theta'])
    
    # Highlight the APOD focus body
    df['Highlight'] = df['Body'].apply(lambda x: 'APOD Focus' if x.lower() == apod_body.lower() else 'Solar System Body')
    
    fig = px.scatter(
        df, 
        x='x', 
        y='y', 
        size='Size', 
        color='Highlight', 
        color_discrete_map={'APOD Focus': '#FF0000', 'Solar System Body': '#808080'},
        hover_data={'Body': True, 'Radius (AU)': True, 'x': False, 'y': False, 'Size': False},
        title="Simplified Solar System Plane (Not to Scale)"
    )

    # Customize plot appearance for a dark 'space' look
    fig.update_traces(marker=dict(line=dict(width=1, color='Black')))
    fig.update_layout(
        xaxis_title="", yaxis_title="", showlegend=True,
        plot_bgcolor='black', paper_bgcolor='#0E1117', font_color='white', height=500
    )
    fig.update_xaxes(scaleanchor="y", scaleratio=1, showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)
    
    return fig

# --- Main Streamlit UI ---

# --- Sidebar Controls ---
st.sidebar.markdown(
    """
    ## 📅 Choose a Date
    Enter a date below to explore the Astronomy Picture of the Day from the NASA archive.
    """
)

# Use st.date_input for better UX, defaulting to today
selected_date = st.sidebar.date_input(
    "Select Date:", 
    value="today", 
    max_value=date.today(),
    min_value=date(1995, 6, 16) # APOD start date
).strftime("%Y-%m-%d")

# Logic to trigger fetch on date change or button click
if st.sidebar.button("🚀 Fetch APOD", use_container_width=True):
    st.session_state['fetch_trigger'] = selected_date
    st.session_state['fetch_by_button'] = True
else:
    # Initial load or date change
    if 'fetch_trigger' not in st.session_state or st.session_state.get('last_selected_date') != selected_date:
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
        with st.spinner(f"Fetching APOD for *{fetch_date}*..."):
            # Pass None if date is today to optimize API call
            data = fetch_apod(None if fetch_date == date.today().strftime("%Y-%m-%d") else fetch_date)
            
            # Extract data
            title = data.get("title", "Untitled APOD")
            apod_date = data.get("date", "Unknown Date")
            explanation = data.get("explanation", "No detailed description provided for this picture.")
            img_url = data.get("url")
            hd_url = data.get("hdurl")

        # Celebration on button click
        if st.session_state.get('fetch_by_button', False):
            st.balloons()
            st.session_state['fetch_by_button'] = False

        ## Display APOD Content
        
        st.header(f"✨ {title}")
        st.caption(f"📅 Date: *{apod_date}*")
        st.markdown("---")

        # Two-column layout for media and explanation
        col1, col2 = st.columns([7, 5]) 

        with col1:
            st.subheader("Media")
            media_type = data.get("media_type", "image")

            if media_type == "video":
                # Embed video directly
                st.video(img_url)
                st.info(f"Today's APOD is a *Video*. If it doesn't load above, [Watch on NASA/YouTube]({img_url})")
            
            elif media_type == "image":
                try:
                    img_response = requests.get(img_url)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content))
                    
                    # Image with subtle border
                    st.markdown(
                        f'<div style="border: 2px solid #367c9c; border-radius: 8px; overflow: hidden;">',
                        unsafe_allow_html=True
                    )
                    st.image(img, caption=f"Viewed on {apod_date}", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if hd_url:
                        # HD Download link
                        st.markdown(f"[🖼 Download HD Image]({hd_url})", unsafe_allow_html=True)

                except requests.exceptions.HTTPError as e:
                    st.error(f"Could not load image file from URL. Error: {e}")
                except Exception as e:
                    st.error(f"An error occurred while processing the image: {e}")
            
            else:
                st.warning(f"Unsupported media type: {media_type}. [View Content Here]({img_url})")

        with col2:
            st.subheader("Explanation")
            # Use expander for long text
            with st.expander("Read Full Description", expanded=True):
                st.markdown(explanation)
                
            st.markdown("*")
            st.markdown("Credit & Source: *NASA/APOD*")

        
        # -------------------------------------------------------------
        # SOLAR SYSTEM CONTEXT AND 3D LINK
        # -------------------------------------------------------------

        solar_system_keywords = ['mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'moon', 'sun', 'comet', 'asteroid', 'aurora', 'planet', 'probe']
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

            # 1. Display Internal Plotly Visualization
            try:
                solar_fig = get_solar_system_plot(main_body)
                st.plotly_chart(solar_fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not generate solar system plot: {e}")
                
            st.markdown("---")

            # 2. Add External 3D Visualization Link
            nasa_eyes_url = "https://eyes.nasa.gov/apps/solar-system/#/home" 
            
            # Construct a more specific link for the external 3D viewer (best effort)
            if main_body != 'Sun':
                nasa_eyes_url = f"https://eyes.nasa.gov/apps/solar-system/#/scenarios/planets/Solarsystem/Planet%20View/{main_body}"
                
            st.markdown("### 🚀 Explore the Location in 3D!")
            
            st.link_button(
                label=f"Click to View {main_body} in NASA's Interactive 3D Model", 
                url=nasa_eyes_url,
                help="Opens the NASA Eyes on the Solar System website in a new tab.",
                type="primary"
            )
            
            st.caption("You will be redirected to an external NASA website for the interactive 3D view.")
        
    except Exception as e:
        st.error(f"An error occurred while fetching the APOD: {e}")
        st.info("Please ensure the date is correctly formatted (YYYY-MM-DD) and not a future date.")

