"""
Sri Lanka Disaster Dashboard - Streamlit App

An interactive dashboard displaying real-time flood and disaster data from the
Disaster Management Centre (DMC) of Sri Lanka.

Includes:
- Situation Reports: Flood impact by district
- Landslide Warnings: Active landslide alerts
- Flood Warnings: Active flood alerts
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from pathlib import Path
from datetime import datetime
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import get_latest_sitrep, download_pdf
from pdf_extractor import extract_sitrep_data, convert_to_geojson

# Page configuration
st.set_page_config(
    page_title="Sri Lanka Disaster Dashboard",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DMC Report URLs
DMC_URLS = {
    "sitrep": "https://www.dmc.gov.lk/index.php?option=com_content&view=article&id=89&Itemid=308&lang=en",
    "landslide": "https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en",
    "flood": "https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=277&report_type_id=6&lang=en",
}

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SITREPS_DIR = DATA_DIR / "sitreps"
DISTRICTS_GEOJSON = DATA_DIR / "districts.geojson"
LATEST_DATA_FILE = SITREPS_DIR / "latest.json"

# Ensure directories exist
SITREPS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

def load_districts_geojson() -> dict:
    """Load the districts boundary GeoJSON."""
    with open(DISTRICTS_GEOJSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_latest_data() -> dict | None:
    """Load the most recent extracted data."""
    if LATEST_DATA_FILE.exists():
        with open(LATEST_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_data(data: dict, filename: str = "latest.json") -> None:
    """Save extracted data to file."""
    filepath = SITREPS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_and_extract_data() -> dict:
    """
    Run the full pipeline: scrape DMC website, download PDF, extract data.
    """
    # Fetch latest sitrep metadata
    sitrep = get_latest_sitrep()
    if not sitrep:
        raise ValueError("Could not find any situation reports on DMC website")
    
    # Download PDF
    pdf_bytes = download_pdf(sitrep["pdf_url"])
    
    # Extract data from PDF
    data = extract_sitrep_data(pdf_bytes)
    data["metadata"]["pdf_url"] = sitrep["pdf_url"]
    data["metadata"]["scraped_title"] = sitrep.get("title", "")
    
    return data


# ============================================================
# MAP FUNCTIONS
# ============================================================

def create_choropleth_map(data: dict | None, districts_geojson: dict) -> folium.Map:
    """Create a Folium choropleth map with flood data."""
    sri_lanka_center = [7.8731, 80.7718]
    
    m = folium.Map(
        location=sri_lanka_center,
        zoom_start=7,
        tiles="cartodbpositron"
    )
    
    # Create a lookup dictionary for district data
    district_data_lookup = {}
    if data and "districts" in data:
        for d in data["districts"]:
            district_data_lookup[d["district"]] = d
    
    # Add district data to GeoJSON properties
    for feature in districts_geojson["features"]:
        district_name = feature["properties"].get("district", "")
        if district_name in district_data_lookup:
            district_info = district_data_lookup[district_name]
            feature["properties"].update({
                "people_affected": district_info.get("people_affected", 0),
                "families_affected": district_info.get("families_affected", 0),
                "deaths": district_info.get("deaths", 0),
                "missing": district_info.get("missing", 0),
                "houses_fully_damaged": district_info.get("houses_fully_damaged", 0),
                "houses_partially_damaged": district_info.get("houses_partially_damaged", 0),
                "people_displaced": district_info.get("people_displaced", 0),
            })
        else:
            feature["properties"].update({
                "people_affected": 0,
                "families_affected": 0,
                "deaths": 0,
                "missing": 0,
                "houses_fully_damaged": 0,
                "houses_partially_damaged": 0,
                "people_displaced": 0,
            })
    
    # Style function for coloring
    def style_function(feature):
        value = feature['properties'].get('people_affected', 0)
        return {
            'fillColor': get_color(value),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7,
        }
    
    def highlight_function(feature):
        return {
            'fillColor': '#000000',
            'color': '#000000',
            'weight': 3,
            'fillOpacity': 0.5,
        }
    
    # Tooltip
    tooltip = folium.GeoJsonTooltip(
        fields=["district", "people_affected", "deaths", "missing", "people_displaced"],
        aliases=["District:", "People Affected:", "Deaths:", "Missing:", "Displaced:"],
        localize=True,
        sticky=True,
        labels=True,
        style="""
            background-color: white;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
            font-size: 14px;
            padding: 10px;
        """,
    )
    
    folium.GeoJson(
        districts_geojson,
        name="District Details",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=tooltip,
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return m


def create_empty_map(title: str) -> folium.Map:
    """Create an empty base map of Sri Lanka."""
    sri_lanka_center = [7.8731, 80.7718]
    
    m = folium.Map(
        location=sri_lanka_center,
        zoom_start=7,
        tiles="cartodbpositron"
    )
    
    # Add a title marker
    folium.Marker(
        location=sri_lanka_center,
        popup=f"<b>{title}</b><br>Data not yet loaded",
        icon=folium.Icon(color="gray", icon="info-sign"),
    ).add_to(m)
    
    return m


def get_color(value: int) -> str:
    """Get color based on affected population value."""
    if value == 0:
        return '#f7f7f7'
    elif value < 1000:
        return '#fee5d9'
    elif value < 5000:
        return '#fcae91'
    elif value < 20000:
        return '#fb6a4a'
    elif value < 50000:
        return '#de2d26'
    else:
        return '#a50f15'


# ============================================================
# DISPLAY HELPER FUNCTIONS
# ============================================================

def display_sitrep_stats(data: dict | None) -> None:
    """Display situation report statistics."""
    if data is None:
        st.warning("No data available. Click refresh to fetch.")
        return
    
    totals = data.get("totals", {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Districts Affected", totals.get("districts_affected", 0))
        st.metric("Deaths", totals.get("total_deaths", 0))
        st.metric("Missing", totals.get("total_missing", 0))
    
    with col2:
        st.metric("People Affected", f"{totals.get('total_people_affected', 0):,}")
        st.metric("Families Affected", f"{totals.get('total_families_affected', 0):,}")
        st.metric("People Displaced", f"{totals.get('total_people_displaced', 0):,}")
    
    st.markdown("**🏠 Housing Damage:**")
    st.write(f"- Fully Damaged: {totals.get('total_houses_fully_damaged', 0):,}")
    st.write(f"- Partially Damaged: {totals.get('total_houses_partially_damaged', 0):,}")


def display_top_affected(data: dict | None) -> None:
    """Display top affected districts."""
    if data is None or "districts" not in data:
        st.info("No district data available.")
        return
    
    districts = sorted(
        data["districts"],
        key=lambda x: x.get("people_affected", 0),
        reverse=True
    )[:5]
    
    for i, d in enumerate(districts, 1):
        st.markdown(f"**{i}. {d['district']}**")
        st.caption(f"👥 {d.get('people_affected', 0):,} affected" + 
                  (f" | 💀 {d.get('deaths', 0)} deaths" if d.get('deaths', 0) > 0 else ""))


def display_district_table(data: dict | None) -> None:
    """Display district-level data in a table."""
    if data is None or "districts" not in data:
        st.info("No district data available.")
        return
    
    import pandas as pd
    
    districts = data["districts"]
    df = pd.DataFrame(districts)
    
    display_columns = {
        "district": "District",
        "people_affected": "People Affected",
        "families_affected": "Families Affected",
        "deaths": "Deaths",
        "missing": "Missing",
        "people_displaced": "Displaced",
        "houses_fully_damaged": "Houses Fully Damaged",
        "houses_partially_damaged": "Houses Partially Damaged",
    }
    
    df_display = df[[c for c in display_columns.keys() if c in df.columns]]
    df_display = df_display.rename(columns=display_columns)
    df_display = df_display.sort_values("People Affected", ascending=False)
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB RENDERING FUNCTIONS
# ============================================================

def render_sitrep_tab(districts_geojson: dict):
    """Render the Situation Reports tab."""
    st.header("📊 Flood Situation Reports")
    st.markdown("""
    Current flood impact data extracted from official DMC situation reports.
    Click **Refresh Data** to fetch the latest report.
    """)
    
    # Refresh button
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refresh Sitrep Data", use_container_width=True, type="primary"):
            with st.spinner("Fetching latest situation report from DMC..."):
                try:
                    data = fetch_and_extract_data()
                    st.session_state.sitrep_data = data
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                    save_data(data, f"sitrep_{timestamp}.json")
                    save_data(data, "latest.json")
                    
                    st.success("✅ Situation report updated!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col_info:
        if st.session_state.sitrep_data:
            metadata = st.session_state.sitrep_data.get("metadata", {})
            report_date = metadata.get("report_date_formatted", metadata.get("report_date_raw", "Unknown"))
            st.info(f"📅 **Last Report:** {report_date}")
            if "pdf_url" in metadata:
                st.markdown(f"[📄 View Original PDF]({metadata['pdf_url']})")
    
    st.divider()
    
    # Main content - Map and Stats
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ Flood Impact Map")
        m = create_choropleth_map(st.session_state.sitrep_data, districts_geojson)
        st_folium(m, width=700, height=500, returned_objects=[])
        st.caption("**Legend:** Color intensity = number of people affected")
    
    with col2:
        st.subheader("📈 Summary Statistics")
        display_sitrep_stats(st.session_state.sitrep_data)
        
        st.divider()
        
        st.subheader("🔝 Top Affected")
        display_top_affected(st.session_state.sitrep_data)
    
    # District table
    st.divider()
    with st.expander("📋 View All District Data", expanded=False):
        display_district_table(st.session_state.sitrep_data)


def render_landslide_tab(districts_geojson: dict):
    """Render the Landslide Warnings tab."""
    st.header("⛰️ Landslide Warnings")
    st.markdown(f"""
    Active landslide warnings from DMC.  
    **Source:** [DMC Landslide Reports]({DMC_URLS['landslide']})
    """)
    
    # Refresh button
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refresh Landslide Data", use_container_width=True, type="primary"):
            with st.spinner("Fetching landslide warnings..."):
                # TODO: Implement landslide data scraping
                st.info("🚧 Landslide scraping not yet implemented")
                st.session_state.landslide_data = None
    
    with col_info:
        if st.session_state.landslide_data:
            st.info("📅 **Last Updated:** Data available")
        else:
            st.warning("No landslide data loaded. Click refresh to fetch.")
    
    st.divider()
    
    # Placeholder content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ Landslide Warning Map")
        m = create_empty_map("Landslide Warnings")
        st_folium(m, width=700, height=500, returned_objects=[])
        st.caption("🚧 Map will show landslide risk areas when data is available")
    
    with col2:
        st.subheader("⚠️ Active Warnings")
        
        if st.session_state.landslide_data:
            st.write("Landslide data will appear here")
        else:
            st.info("""
            **Coming Soon:**
            - Active landslide warnings by district
            - Risk level indicators
            - Affected areas list
            """)
        
        st.divider()
        
        st.subheader("📊 Risk Levels")
        st.markdown("""
        - 🔴 **High Risk** - Immediate danger
        - 🟠 **Medium Risk** - Caution advised
        - 🟡 **Low Risk** - Monitor situation
        - 🟢 **No Warning** - Safe
        """)


def render_flood_tab(districts_geojson: dict):
    """Render the Flood Warnings tab."""
    st.header("🌊 Flood Warnings")
    st.markdown(f"""
    Active flood warnings from DMC.  
    **Source:** [DMC Flood Reports]({DMC_URLS['flood']})
    """)
    
    # Refresh button
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refresh Flood Data", use_container_width=True, type="primary"):
            with st.spinner("Fetching flood warnings..."):
                # TODO: Implement flood warning data scraping
                st.info("🚧 Flood warning scraping not yet implemented")
                st.session_state.flood_data = None
    
    with col_info:
        if st.session_state.flood_data:
            st.info("📅 **Last Updated:** Data available")
        else:
            st.warning("No flood warning data loaded. Click refresh to fetch.")
    
    st.divider()
    
    # Placeholder content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ Flood Warning Map")
        m = create_empty_map("Flood Warnings")
        st_folium(m, width=700, height=500, returned_objects=[])
        st.caption("🚧 Map will show flood risk areas when data is available")
    
    with col2:
        st.subheader("⚠️ Active Warnings")
        
        if st.session_state.flood_data:
            st.write("Flood warning data will appear here")
        else:
            st.info("""
            **Coming Soon:**
            - Active flood warnings by river basin
            - Water level alerts
            - Evacuation notices
            """)
        
        st.divider()
        
        st.subheader("📊 Alert Levels")
        st.markdown("""
        - 🔴 **Danger** - Flooding imminent
        - 🟠 **Warning** - Prepare for flooding
        - 🟡 **Watch** - Monitor water levels
        - 🟢 **Normal** - No flooding expected
        """)


# ============================================================
# MAIN APP
# ============================================================

def main():
    """Main application entry point."""
    # Title and description
    st.title("🇱🇰 Sri Lanka Disaster Dashboard")
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
    if "landslide_data" not in st.session_state:
        st.session_state.landslide_data = None
    if "flood_data" not in st.session_state:
        st.session_state.flood_data = None
    
    # Sidebar
    st.sidebar.title("🇱🇰 DMC Dashboard")
    st.sidebar.markdown("""
    Monitor disasters in Sri Lanka:
    - 📊 Situation Reports
    - ⛰️ Landslide Warnings  
    - 🌊 Flood Warnings
    """)
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Data Source:**  \n[Disaster Management Centre](https://www.dmc.gov.lk)")
    
    # Create main tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Situation Reports",
        "⛰️ Landslide Warnings",
        "🌊 Flood Warnings"
    ])
    
    # Render tabs
    with tab1:
        render_sitrep_tab(districts_geojson)
    
    with tab2:
        render_landslide_tab(districts_geojson)
    
    with tab3:
        render_flood_tab(districts_geojson)
    
    # Footer
    st.divider()
    st.markdown("""
    ---
    **Data Source:** [Disaster Management Centre, Sri Lanka](https://www.dmc.gov.lk)  
    **Built with:** Streamlit, Folium, PyMuPDF
    """)


if __name__ == "__main__":
    main()
