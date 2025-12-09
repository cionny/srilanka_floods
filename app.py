"""
Sri Lanka Disaster Dashboard - Streamlit App

An interactive dashboard displaying real-time flood and disaster data from the
Disaster Management Centre (DMC) of Sri Lanka.

Includes:
- Situation Reports: Flood impact by district
- Landslide Warnings: Active landslide alerts
- Flood Warnings: Active flood alerts
- Dynamic Analytical Brief: AI-powered trend analysis
"""

import streamlit as st
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import from modular components
from src.data_manager import (
    SITREPS_DIR,
    DMC_URLS,
    load_districts_geojson,
    load_latest_data,
    load_previous_data,
    load_landslide_data,
)
from src.trend_analyzer import generate_trend_summary
from src.tabs import (
    render_sitrep_tab,
    render_landslide_tab,
    render_flood_tab,
    render_analytics_tab,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Sri Lanka Disaster Dashboard",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# MAIN APP
# ============================================================

def main():
    """Main application entry point."""
    # Title and description
    st.title("🇱🇰 Sri Lanka Monitoring Dashboard")
    st.caption("⚠️ This is a test project, do not take any operational decisions based on this dashboard.")
    st.markdown("""
    Real-time disaster monitoring using data from the 
    [Disaster Management Centre (DMC)](https://www.dmc.gov.lk) of Sri Lanka.
    """)
    
    # Load districts GeoJSON
    try:
        districts_geojson = load_districts_geojson()
    except FileNotFoundError:
        st.error("Districts GeoJSON file not found. Please ensure data/districts.geojson exists.")
        return
    
    # Initialize session state for all data types
    if "sitrep_data" not in st.session_state:
        st.session_state.sitrep_data = load_latest_data()
    if "previous_sitrep_data" not in st.session_state:
        st.session_state.previous_sitrep_data = load_previous_data()
    if "landslide_data" not in st.session_state:
        st.session_state.landslide_data = load_landslide_data()
    if "flood_data" not in st.session_state:
        st.session_state.flood_data = None
    if "selected_metric" not in st.session_state:
        st.session_state.selected_metric = "people_affected"
    
    # Sidebar
    render_sidebar()
    
    # Create main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Situation Reports",
        "⛰️ Landslide Warnings",
        "🌊 Flood Warnings",
        "🤖 Dynamic Analytical Brief"
    ])
    
    # Render tabs
    with tab1:
        render_sitrep_tab(districts_geojson)
    
    with tab2:
        render_landslide_tab(districts_geojson)
    
    with tab3:
        render_flood_tab(districts_geojson)
    
    with tab4:
        render_analytics_tab(SITREPS_DIR, generate_trend_summary)
    
    # Footer
    render_footer()


def render_sidebar():
    """Render the sidebar with info and links."""
    st.sidebar.title("Monitoring Dashboard")
    
    # How it works section
    st.sidebar.subheader("⚙️ How It Works")
    st.sidebar.markdown("""
    1. **Scrape** the DMC website for latest reports
    2. **Download** PDF reports automatically
    3. **Extract** tables and data using PyMuPDF
    4. **Visualize** on interactive choropleth maps
    
    Click **Refresh** in any tab to fetch the latest data.
    """)
    
    st.sidebar.markdown("---")
    
    # Data sources section
    st.sidebar.subheader("📁 Data Sources")
    st.sidebar.markdown(f"""
    All data from [DMC Sri Lanka](https://www.dmc.gov.lk):
    
    **📊 Situation Reports**  
    Deaths, missing, affected, displaced  
    [View Reports →]({DMC_URLS['sitrep']})
    
    **⛰️ Landslide Warnings**  
    Alert levels by district/division  
    [View Reports →]({DMC_URLS['landslide']})
    
    **🌊 River Water Levels**  
    Water levels & rainfall data  
    [View Reports →]({DMC_URLS['flood']})
    
    **🌤️ Weather Forecasts**  
    Weather forecasts & reports  
    [View Reports →]({DMC_URLS.get('weather', DMC_URLS['sitrep'])})
    """)


def render_footer():
    """Render the footer with credits."""
    st.divider()
    st.markdown("""
    ---
    **Data Source:** [Disaster Management Centre, Sri Lanka](https://www.dmc.gov.lk)  
    **Built with:** Streamlit, Folium, PyMuPDF
    """)


if __name__ == "__main__":
    main()
