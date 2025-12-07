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
import streamlit.components.v1 as components
import folium
import json
from pathlib import Path
from datetime import datetime
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import get_latest_sitrep, get_latest_two_sitreps, download_pdf
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
PREVIOUS_DATA_FILE = SITREPS_DIR / "previous.json"

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


def load_previous_data() -> dict | None:
    """Load the previous extracted data for comparison."""
    if PREVIOUS_DATA_FILE.exists():
        with open(PREVIOUS_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_data(data: dict, filename: str = "latest.json") -> None:
    """Save extracted data to file."""
    filepath = SITREPS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_and_extract_data() -> tuple[dict, dict | None]:
    """
    Run the full pipeline: scrape DMC website, download PDFs, extract data.
    
    Returns:
        Tuple of (latest_data, previous_data). previous_data may be None.
    """
    # Fetch latest two sitrep metadata
    latest_sitrep, previous_sitrep = get_latest_two_sitreps()
    
    if not latest_sitrep:
        raise ValueError("Could not find any situation reports on DMC website")
    
    # Download and extract latest PDF
    pdf_bytes = download_pdf(latest_sitrep["pdf_url"])
    latest_data = extract_sitrep_data(pdf_bytes)
    latest_data["metadata"]["pdf_url"] = latest_sitrep["pdf_url"]
    latest_data["metadata"]["scraped_title"] = latest_sitrep.get("title", "")
    
    # Download and extract previous PDF if available
    previous_data = None
    if previous_sitrep:
        try:
            pdf_bytes = download_pdf(previous_sitrep["pdf_url"])
            previous_data = extract_sitrep_data(pdf_bytes)
            previous_data["metadata"]["pdf_url"] = previous_sitrep["pdf_url"]
            previous_data["metadata"]["scraped_title"] = previous_sitrep.get("title", "")
        except Exception as e:
            print(f"Warning: Could not fetch previous report: {e}")
            previous_data = None
    
    return latest_data, previous_data


# ============================================================
# MAP FUNCTIONS
# ============================================================

# Metric configuration for map visualization
# Thresholds are tuned based on actual data distribution
METRIC_CONFIG = {
    "people_affected": {
        "label": "People Affected",
        # Range: 1,671 to 433,036 - need 6 meaningful buckets
        "thresholds": [0, 10000, 50000, 100000, 200000, 350000],
        "format": "{:,}",
    },
    "deaths": {
        "label": "Deaths",
        # Range: 0 to ~90
        "thresholds": [0, 5, 15, 30, 50, 75],
        "format": "{}",
    },
    "missing": {
        "label": "Missing",
        # Range: 0 to ~20
        "thresholds": [0, 2, 5, 10, 15, 20],
        "format": "{}",
    },
    "houses_fully_damaged": {
        "label": "Houses Fully Damaged",
        # Range: 0 to ~600
        "thresholds": [0, 20, 50, 100, 300, 500],
        "format": "{:,}",
    },
    "houses_partially_damaged": {
        "label": "Houses Partially Damaged",
        # Range: 0 to ~7000
        "thresholds": [0, 500, 1000, 2000, 4000, 6000],
        "format": "{:,}",
    },
    "people_displaced": {
        "label": "People Displaced",
        # Range: 0 to ~31,000
        "thresholds": [0, 1000, 3000, 6000, 12000, 25000],
        "format": "{:,}",
    },
}


def get_color_for_metric(value: int, metric: str) -> str:
    """Get color based on value and metric-specific thresholds."""
    config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    thresholds = config["thresholds"]
    
    # Color palette (light to dark red) - 7 colors for 6 thresholds
    colors = ['#f7f7f7', '#fef0d9', '#fdcc8a', '#fc8d59', '#e34a33', '#b30000', '#7f0000']
    
    if value == 0:
        return colors[0]
    elif value < thresholds[1]:
        return colors[1]
    elif value < thresholds[2]:
        return colors[2]
    elif value < thresholds[3]:
        return colors[3]
    elif value < thresholds[4]:
        return colors[4]
    elif value < thresholds[5]:
        return colors[5]
    else:
        return colors[6]


def create_choropleth_map(data: dict | None, districts_geojson: dict, metric: str = "people_affected") -> folium.Map:
    """Create a Folium choropleth map with flood data.
    
    Args:
        data: Extracted sitrep data with districts
        districts_geojson: GeoJSON with district boundaries
        metric: The metric to visualize (e.g., 'people_affected', 'deaths')
    """
    import copy
    
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
    
    # Deep copy to avoid mutating original
    geojson_copy = copy.deepcopy(districts_geojson)
    
    # Add district data and pre-compute styles in GeoJSON properties
    for feature in geojson_copy["features"]:
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
        
        # Pre-compute fill color based on selected metric
        metric_value = feature["properties"].get(metric, 0)
        feature["properties"]["_fill_color"] = get_color_for_metric(metric_value, metric)
    
    # Get metric config for formatting
    metric_config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    metric_label = metric_config["label"].split(" ", 1)[1]  # Remove emoji
    
    # Add each feature individually with inline style (avoids function serialization)
    for feature in geojson_copy["features"]:
        fill_color = feature["properties"].get("_fill_color", "#f7f7f7")
        
        # Create tooltip HTML with all metrics, highlighting the selected one
        props = feature["properties"]
        
        def format_metric_line(key: str, label: str, value: int, is_selected: bool) -> str:
            formatted = f"{value:,}" if value >= 1000 else str(value)
            if is_selected:
                return f"<b style='color: #de2d26;'>{label}: {formatted}</b>"
            return f"{label}: {formatted}"
        
        tooltip_html = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>{props.get('district', 'Unknown')}</b><br>
            {format_metric_line('people_affected', 'People Affected', props.get('people_affected', 0), metric == 'people_affected')}<br>
            {format_metric_line('deaths', 'Deaths', props.get('deaths', 0), metric == 'deaths')}<br>
            {format_metric_line('missing', 'Missing', props.get('missing', 0), metric == 'missing')}<br>
            {format_metric_line('houses_fully_damaged', 'Houses Fully Damaged', props.get('houses_fully_damaged', 0), metric == 'houses_fully_damaged')}<br>
            {format_metric_line('houses_partially_damaged', 'Houses Partially Damaged', props.get('houses_partially_damaged', 0), metric == 'houses_partially_damaged')}<br>
            {format_metric_line('people_displaced', 'People Displaced', props.get('people_displaced', 0), metric == 'people_displaced')}
        </div>
        """
        
        folium.GeoJson(
            feature,
            style_function=lambda x, fc=fill_color: {
                'fillColor': fc,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7,
            },
            tooltip=folium.Tooltip(tooltip_html),
        ).add_to(m)
    
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
    """Get color based on affected population value (legacy function)."""
    return get_color_for_metric(value, "people_affected")


def get_legend_html(metric: str) -> str:
    """Generate HTML legend for the selected metric."""
    config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    thresholds = config["thresholds"]
    # Match the color palette in get_color_for_metric
    colors = ['#f7f7f7', '#fef0d9', '#fdcc8a', '#fc8d59', '#e34a33', '#b30000', '#7f0000']
    
    def fmt(n):
        """Format number with K/M suffix for readability."""
        if n >= 1000000:
            return f"{n/1000000:.1f}M"
        elif n >= 1000:
            return f"{n/1000:.0f}K"
        return str(n)
    
    legend_items = [
        f"<span style='background:{colors[0]};padding:2px 6px;border:1px solid #ccc;font-size:11px;'>0</span>",
        f"<span style='background:{colors[1]};padding:2px 6px;border:1px solid #ccc;font-size:11px;'>1-{fmt(thresholds[1]-1)}</span>",
        f"<span style='background:{colors[2]};padding:2px 6px;border:1px solid #ccc;font-size:11px;'>{fmt(thresholds[1])}-{fmt(thresholds[2]-1)}</span>",
        f"<span style='background:{colors[3]};padding:2px 6px;border:1px solid #ccc;font-size:11px;'>{fmt(thresholds[2])}-{fmt(thresholds[3]-1)}</span>",
        f"<span style='background:{colors[4]};padding:2px 6px;border:1px solid #ccc;font-size:11px;color:white;'>{fmt(thresholds[3])}-{fmt(thresholds[4]-1)}</span>",
        f"<span style='background:{colors[5]};padding:2px 6px;border:1px solid #ccc;font-size:11px;color:white;'>{fmt(thresholds[4])}-{fmt(thresholds[5]-1)}</span>",
        f"<span style='background:{colors[6]};padding:2px 6px;border:1px solid #ccc;font-size:11px;color:white;'>{fmt(thresholds[5])}+</span>",
    ]
    
    return " ".join(legend_items)


# ============================================================
# DISPLAY HELPER FUNCTIONS
# ============================================================

def display_sitrep_stats(data: dict | None, previous_data: dict | None = None) -> None:
    """Display situation report statistics with comparison to previous report."""
    if data is None:
        st.warning("No data available. Click refresh to fetch.")
        return
    
    totals = data.get("totals", {})
    prev_totals = previous_data.get("totals", {}) if previous_data else {}
    
    def get_delta(key: str) -> int | None:
        """Calculate delta between current and previous value."""
        if not prev_totals:
            return None
        current = totals.get(key, 0)
        previous = prev_totals.get(key, 0)
        return current - previous if previous else None
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Districts Affected", 
            totals.get("districts_affected", 0),
            delta=get_delta("districts_affected"),
            delta_color="inverse"  # More districts = worse
        )
        st.metric(
            "Deaths", 
            totals.get("total_deaths", 0),
            delta=get_delta("total_deaths"),
            delta_color="inverse"  # More deaths = worse
        )
        st.metric(
            "Missing", 
            totals.get("total_missing", 0),
            delta=get_delta("total_missing"),
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "People Affected", 
            f"{totals.get('total_people_affected', 0):,}",
            delta=f"{get_delta('total_people_affected'):,}" if get_delta('total_people_affected') else None,
            delta_color="inverse"
        )
        st.metric(
            "Families Affected", 
            f"{totals.get('total_families_affected', 0):,}",
            delta=f"{get_delta('total_families_affected'):,}" if get_delta('total_families_affected') else None,
            delta_color="inverse"
        )
        st.metric(
            "People Displaced", 
            f"{totals.get('total_people_displaced', 0):,}",
            delta=f"{get_delta('total_people_displaced'):,}" if get_delta('total_people_displaced') else None,
            delta_color="inverse"
        )
    
    # Housing damage with deltas
    fully_damaged = totals.get('total_houses_fully_damaged', 0)
    partially_damaged = totals.get('total_houses_partially_damaged', 0)
    fully_delta = get_delta('total_houses_fully_damaged')
    partially_delta = get_delta('total_houses_partially_damaged')
    
    st.markdown("**🏠 Housing Damage:**")
    
    fully_text = f"- Fully Damaged: {fully_damaged:,}"
    if fully_delta:
        arrow = "↑" if fully_delta > 0 else "↓" if fully_delta < 0 else ""
        fully_text += f" ({'+' if fully_delta > 0 else ''}{fully_delta:,} {arrow})"
    st.write(fully_text)
    
    partially_text = f"- Partially Damaged: {partially_damaged:,}"
    if partially_delta:
        arrow = "↑" if partially_delta > 0 else "↓" if partially_delta < 0 else ""
        partially_text += f" ({'+' if partially_delta > 0 else ''}{partially_delta:,} {arrow})"
    st.write(partially_text)


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
            with st.spinner("Fetching latest situation reports from DMC..."):
                try:
                    latest_data, previous_data = fetch_and_extract_data()
                    st.session_state.sitrep_data = latest_data
                    st.session_state.previous_sitrep_data = previous_data
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                    save_data(latest_data, f"sitrep_{timestamp}.json")
                    save_data(latest_data, "latest.json")
                    if previous_data:
                        save_data(previous_data, "previous.json")
                    
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
        
        # Metric selector dropdown
        metric_options = {v["label"]: k for k, v in METRIC_CONFIG.items()}
        selected_label = st.selectbox(
            "Select metric to visualize:",
            options=list(metric_options.keys()),
            index=0,
            key="map_metric_selector"
        )
        selected_metric = metric_options[selected_label]
        
        # Create and display map with selected metric
        m = create_choropleth_map(st.session_state.sitrep_data, districts_geojson, metric=selected_metric)
        components.html(m._repr_html_(), height=500)
        
        # Dynamic legend
        st.markdown(f"**Legend ({selected_label.split(' ', 1)[1]}):** {get_legend_html(selected_metric)}", unsafe_allow_html=True)
    
    with col2:
        st.subheader("📈 Summary Statistics")
        display_sitrep_stats(st.session_state.sitrep_data, st.session_state.previous_sitrep_data)
        
        # Show comparison info if previous data exists
        if st.session_state.previous_sitrep_data:
            prev_meta = st.session_state.previous_sitrep_data.get("metadata", {})
            prev_date = prev_meta.get("report_date_formatted", prev_meta.get("report_date_raw", "Unknown"))
            st.caption(f"📅 Compared to: {prev_date}")
        
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
        components.html(m._repr_html_(), height=500)
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
        components.html(m._repr_html_(), height=500)
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
        st.session_state.landslide_data = None
    if "flood_data" not in st.session_state:
        st.session_state.flood_data = None
    
    # Sidebar
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
    st.sidebar.markdown("""
    All data from [DMC Sri Lanka](https://www.dmc.gov.lk):
    
    **📊 Situation Reports**  
    Deaths, missing, affected, displaced  
    [View Reports →](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=273&report_type_id=1&lang=en)
    
    **⛰️ Landslide Warnings**  
    Alert levels by district/division  
    [View Reports →](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en)
    
    **🌊 River Water Levels**  
    Water levels & rainfall data  
    [View Reports →](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en)
    
    **🌤️ Weather Forecasts**  
    Weather forecasts & reports  
    [View Reports →](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=274&report_type_id=2&lang=en)
    """)
    
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
