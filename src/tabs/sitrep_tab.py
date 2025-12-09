"""
Situation Reports tab for the Sri Lanka Monitoring Dashboard.
Handles the display of DMC situation report data with choropleth maps.
"""

import json
import copy
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from src.data_manager import (
    DMC_URLS,
    fetch_and_extract_data,
    save_data,
)
from src.map_utils import (
    METRIC_CONFIG,
    create_choropleth_map,
    get_legend_html,
)


# ============================================================
# DISPLAY HELPER FUNCTIONS
# ============================================================

def display_sitrep_stats(
    sitrep_data: dict | None, 
    previous_data: dict | None = None,
    selected_district: str = "All Districts"
):
    """Display summary statistics for situation report data."""
    if not sitrep_data:
        st.info("No situation report data loaded. Click **Refresh Sitrep Data** to fetch.")
        return
    
    # Get data based on selection
    if selected_district == "All Districts":
        totals = sitrep_data.get("totals", {})
        prev_totals = previous_data.get("totals", {}) if previous_data else {}
    else:
        # Find the selected district
        districts = sitrep_data.get("districts", [])
        district_data = next((d for d in districts if d.get("district") == selected_district), None)
        totals = district_data if district_data else {}
        
        # Find previous district data
        if previous_data:
            prev_districts = previous_data.get("districts", [])
            prev_district_data = next((d for d in prev_districts if d.get("district") == selected_district), None)
            prev_totals = prev_district_data if prev_district_data else {}
        else:
            prev_totals = {}
    
    # Calculate deltas
    def get_delta(current: int, previous: int) -> str | None:
        if previous > 0:
            diff = current - previous
            return f"{diff:+,}" if diff != 0 else None
        return None
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # Handle both totals (total_*) and district field names
    affected = totals.get("total_people_affected", totals.get("people_affected", 0))
    prev_affected = prev_totals.get("total_people_affected", prev_totals.get("people_affected", 0))
    
    displaced = totals.get("total_people_displaced", totals.get("people_displaced", 0))
    prev_displaced = prev_totals.get("total_people_displaced", prev_totals.get("people_displaced", 0))
    
    deaths = totals.get("total_deaths", totals.get("deaths", 0))
    prev_deaths = prev_totals.get("total_deaths", prev_totals.get("deaths", 0))
    
    missing = totals.get("total_missing", totals.get("missing", 0))
    prev_missing = prev_totals.get("total_missing", prev_totals.get("missing", 0))
    
    fully_damaged = totals.get("total_houses_fully_damaged", totals.get("houses_fully_damaged", 0))
    prev_fully_damaged = prev_totals.get("total_houses_fully_damaged", prev_totals.get("houses_fully_damaged", 0))
    
    partially_damaged = totals.get("total_houses_partially_damaged", totals.get("houses_partially_damaged", 0))
    prev_partially_damaged = prev_totals.get("total_houses_partially_damaged", prev_totals.get("houses_partially_damaged", 0))
    
    with col1:
        st.metric(
            "People Affected", 
            f"{affected:,}",
            delta=get_delta(affected, prev_affected),
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "People Displaced", 
            f"{displaced:,}",
            delta=get_delta(displaced, prev_displaced),
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "Deaths", 
            deaths,
            delta=get_delta(deaths, prev_deaths),
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "Missing", 
            missing,
            delta=get_delta(missing, prev_missing),
            delta_color="inverse"
        )
    
    with col5:
        st.metric(
            "Houses Fully Damaged", 
            f"{fully_damaged:,}",
            delta=get_delta(fully_damaged, prev_fully_damaged),
            delta_color="inverse"
        )
    
    with col6:
        st.metric(
            "Houses Partially Damaged", 
            f"{partially_damaged:,}",
            delta=get_delta(partially_damaged, prev_partially_damaged),
            delta_color="inverse"
        )


def display_top_affected(sitrep_data: dict | None, metric: str = "people_affected", top_n: int = 5):
    """Display the top N affected districts for a given metric."""
    if not sitrep_data:
        st.info("No data available")
        return
    
    districts = sitrep_data.get("districts", [])
    if not districts:
        st.info("No district data available")
        return
    
    config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    format_fn = config["format"]
    
    # Sort by metric
    sorted_districts = sorted(
        districts,
        key=lambda x: x.get(metric, 0),
        reverse=True
    )[:top_n]
    
    for i, d in enumerate(sorted_districts, 1):
        value = d.get(metric, 0)
        if value > 0:
            st.markdown(f"**{i}. {d['district']}:** {format_fn(value)}")


def display_district_table(sitrep_data: dict | None):
    """Display a table with all district data."""
    if not sitrep_data:
        st.info("No data available")
        return
    
    districts = sitrep_data.get("districts", [])
    if not districts:
        st.info("No district data available")
        return
    
    # Create DataFrame
    df = pd.DataFrame(districts)
    
    # Reorder columns - use actual field names from the data
    column_order = ["district", "people_affected", "people_displaced", "deaths", "missing", "houses_fully_damaged", "houses_partially_damaged"]
    available_cols = [c for c in column_order if c in df.columns]
    df = df[available_cols]
    
    # Rename columns for display
    column_rename = {
        "district": "District",
        "people_affected": "People Affected",
        "people_displaced": "People Displaced",
        "deaths": "Deaths", 
        "missing": "Missing",
        "houses_fully_damaged": "Houses Fully Damaged",
        "houses_partially_damaged": "Houses Partially Damaged"
    }
    df = df.rename(columns=column_rename)
    
    # Sort by People Affected
    if "People Affected" in df.columns:
        df = df.sort_values("People Affected", ascending=False)
    
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# TAB RENDER FUNCTION
# ============================================================

def render_sitrep_tab(districts_geojson: dict):
    """Render the Situation Reports tab."""
    st.header("📊 Situation Reports")
    st.markdown(f"""
    Disaster impact data extracted from DMC situation reports.  
    **Source:** [DMC Situation Reports]({DMC_URLS['sitrep']})
    """)
    
    # Refresh button and report info
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
    
    # District filter for summary statistics - small dropdown on the right
    col_stats_label, col_stats_spacer, col_district_filter = st.columns([2, 4, 2])
    
    with col_stats_label:
        st.subheader("📈 Summary Statistics")
    
    with col_district_filter:
        # Build district options
        district_options = ["All Districts"]
        if st.session_state.sitrep_data and "districts" in st.session_state.sitrep_data:
            district_names = sorted([d.get("district", "") for d in st.session_state.sitrep_data["districts"] if d.get("district")])
            district_options.extend(district_names)
        
        selected_district = st.selectbox(
            "Filter by district:",
            options=district_options,
            index=0,
            key="stats_district_filter",
        )
    
    # Summary Statistics row
    display_sitrep_stats(
        st.session_state.sitrep_data, 
        st.session_state.previous_sitrep_data,
        selected_district
    )
    
    # Show comparison info below stats
    if st.session_state.previous_sitrep_data:
        prev_meta = st.session_state.previous_sitrep_data.get("metadata", {})
        prev_date = prev_meta.get("report_date_formatted", prev_meta.get("report_date_raw", "Unknown"))
        st.caption(f"Compared to: {prev_date}")
    
    st.divider()
    
    # Main content - Map (left) and Controls + Top Affected (right)
    col_map, col_sidebar = st.columns([2, 1])
    
    with col_sidebar:
        # Metric selector - compact at top of sidebar
        metric_options = {v["label"]: k for k, v in METRIC_CONFIG.items()}
        selected_label = st.selectbox(
            "Select metric to visualize:",
            options=list(metric_options.keys()),
            index=0,
            key="map_metric_selector",
        )
        selected_metric = metric_options[selected_label]
        
        st.divider()
        
        # Top Affected section
        st.subheader("Top Affected")
        display_top_affected(st.session_state.sitrep_data, metric=selected_metric)
    
    with col_map:
        # Create and display map with selected metric
        m = create_choropleth_map(st.session_state.sitrep_data, districts_geojson, metric=selected_metric)
        components.html(m._repr_html_(), height=620)
        
        # Legend directly below map (no extra spacing)
        st.markdown(f"**Legend ({selected_label}):** {get_legend_html(selected_metric)}", unsafe_allow_html=True)
        
        # Download GeoJSON button
        if st.session_state.sitrep_data:
            # Create GeoJSON with district polygons and sitrep data
            geojson_export = copy.deepcopy(districts_geojson)
            district_data_lookup = {d["district"]: d for d in st.session_state.sitrep_data.get("districts", [])}
            
            for feature in geojson_export["features"]:
                district_name = feature["properties"].get("district", "")
                if district_name in district_data_lookup:
                    feature["properties"].update(district_data_lookup[district_name])
            
            # Add metadata
            geojson_export["metadata"] = st.session_state.sitrep_data.get("metadata", {})
            geojson_export["totals"] = st.session_state.sitrep_data.get("totals", {})
            
            geojson_str = json.dumps(geojson_export, indent=2, ensure_ascii=False)
            
            # Generate filename with sitrep date
            metadata = st.session_state.sitrep_data.get("metadata", {})
            report_date = metadata.get("report_date", "")
            if report_date:
                # Parse and format date for filename (e.g., 2025-12-07_1200)
                try:
                    dt = datetime.fromisoformat(report_date)
                    date_suffix = dt.strftime("%Y-%m-%d_%H%M")
                except:
                    date_suffix = datetime.now().strftime("%Y-%m-%d_%H%M")
            else:
                date_suffix = datetime.now().strftime("%Y-%m-%d_%H%M")
            
            filename = f"sitrep_{date_suffix}.geojson"
            
            st.download_button(
                label="📥 Download GeoJSON",
                data=geojson_str,
                file_name=filename,
                mime="application/geo+json",
            )
    
    # District table at bottom
    st.divider()
    with st.expander("📋 View All District Data", expanded=False):
        display_district_table(st.session_state.sitrep_data)
