"""
Landslide Warnings tab for the Sri Lanka Monitoring Dashboard.
Handles the display of DMC landslide warning data with choropleth maps.
"""

import json
import copy
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from src.scraper import get_latest_landslide_report, download_pdf
from src.landslide_extractor import extract_landslide_data, build_division_lookup
from src.data_manager import (
    DMC_URLS,
    save_landslide_data,
    load_divisions_geojson,
    load_landslide_observations_geojson,
)
from src.map_utils import (
    create_landslide_choropleth_map,
    create_empty_map,
    get_landslide_legend_html,
)


# ============================================================
# DISPLAY HELPER FUNCTIONS
# ============================================================

def display_landslide_table(landslide_data: dict | None):
    """Display a table with all landslide warning data by division."""
    if not landslide_data:
        st.info("No landslide data available")
        return
    
    districts = landslide_data.get("districts", [])
    if not districts:
        st.info("No district data available")
        return
    
    # Flatten to division level
    rows = []
    for district in districts:
        district_name = district.get("district", "Unknown")
        for division in district.get("divisions", []):
            rows.append({
                "district": district_name,
                "division": division.get("division", "Unknown"),
                "warning_level": division.get("warning_level", "Unknown")
            })
    
    if not rows:
        st.info("No division data available")
        return
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Rename columns for display
    df = df.rename(columns={
        "district": "District",
        "division": "Division",
        "warning_level": "Warning Level"
    })
    
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# TAB RENDER FUNCTION
# ============================================================

def render_landslide_tab(districts_geojson: dict, divisions_geojson: dict | None = None):
    """Render the Landslide Warnings tab.
    
    Args:
        districts_geojson: District boundaries GeoJSON for overlay
        divisions_geojson: Division boundaries GeoJSON for detailed coloring
    """
    st.header("⛰️ Landslide Early Warning")
    st.markdown(f"""
    Active landslide warnings by division from DMC.  
    **Source:** [DMC Landslide Reports]({DMC_URLS['landslide']})
    """)
    
    # Refresh button and report info
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refresh Landslide Data", use_container_width=True, type="primary"):
            with st.spinner("Fetching landslide warnings from DMC..."):
                try:
                    # Scrape latest landslide report
                    report = get_latest_landslide_report()
                    if not report:
                        st.error("❌ Could not find any landslide reports on DMC website")
                    else:
                        # Download and extract
                        pdf_bytes = download_pdf(report["pdf_url"])
                        landslide_data = extract_landslide_data(pdf_bytes)
                        landslide_data["metadata"]["pdf_url"] = report["pdf_url"]
                        landslide_data["metadata"]["scraped_title"] = report.get("title", "")
                        
                        # Save to session state and file
                        st.session_state.landslide_data = landslide_data
                        
                        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                        save_landslide_data(landslide_data, f"landslide_{timestamp}.json")
                        save_landslide_data(landslide_data, "latest.json")
                        
                        st.success("✅ Landslide warnings updated!")
                except Exception as e:
                    st.error(f"❌ Error fetching landslide data: {str(e)}")
    
    with col_info:
        if st.session_state.landslide_data:
            metadata = st.session_state.landslide_data.get("metadata", {})
            report_date = metadata.get("report_date_formatted", metadata.get("report_date_raw", "Unknown"))
            st.info(f"📅 **Last Report:** {report_date}")
            if "pdf_url" in metadata:
                st.markdown(f"[📄 View Original PDF]({metadata['pdf_url']})")
        else:
            st.warning("No landslide data loaded. Click refresh to fetch.")
    
    st.divider()
    
    # Summary Statistics
    if st.session_state.landslide_data:
        totals = st.session_state.landslide_data.get("totals", {})
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Districts with Warnings", totals.get("districts_with_warnings", 0))
        with col2:
            st.metric("🔴 Red (Level 3)", 
                      f"{totals.get('total_level_3', 0)} divisions",
                      help="Highest risk - immediate danger")
        with col3:
            st.metric("🟠 Amber (Level 2)", 
                      f"{totals.get('total_level_2', 0)} divisions",
                      help="Medium risk - caution advised")
        with col4:
            st.metric("🟡 Yellow (Level 1)", 
                      f"{totals.get('total_level_1', 0)} divisions",
                      help="Low risk - monitor situation")
        with col5:
            st.metric("Total Divisions Affected", totals.get("total_divisions_affected", 0))
        
        st.divider()
    
    # Main content - Map (left) and Sidebar (right)
    col_map, col_sidebar = st.columns([2, 1])
    
    with col_sidebar:
        st.subheader("⚠️ Active Warnings by District")
        
        if st.session_state.landslide_data:
            districts = st.session_state.landslide_data.get("districts", [])
            
            # Sort by max_level (highest first), then by total_warnings
            sorted_districts = sorted(
                [d for d in districts if d.get("total_warnings", 0) > 0],
                key=lambda x: (x.get("max_level", 0), x.get("total_warnings", 0)),
                reverse=True
            )
            
            if sorted_districts:
                for d in sorted_districts:
                    max_level = d.get("max_level", 0)
                    level_emoji = {0: "⚪", 1: "🟡", 2: "🟠", 3: "🔴"}.get(max_level, "⚪")
                    level_name = {0: "None", 1: "Yellow", 2: "Amber", 3: "Red"}.get(max_level, "None")
                    
                    with st.expander(f"{level_emoji} **{d['district']}** ({d['total_warnings']} divisions)"):
                        if d.get("level_3_divisions"):
                            st.markdown(f"🔴 **Red:** {', '.join(d['level_3_divisions'])}")
                        if d.get("level_2_divisions"):
                            st.markdown(f"🟠 **Amber:** {', '.join(d['level_2_divisions'])}")
                        if d.get("level_1_divisions"):
                            st.markdown(f"🟡 **Yellow:** {', '.join(d['level_1_divisions'])}")
            else:
                st.success("✅ No active landslide warnings!")
        else:
            st.info("Click **Refresh Landslide Data** to load warnings.")
        
        st.divider()
        
        st.subheader("📊 Risk Levels")
        st.markdown("""
        - 🔴 **Level 3 (Red)** - High risk, immediate danger
        - 🟠 **Level 2 (Amber)** - Medium risk, caution advised
        - 🟡 **Level 1 (Yellow)** - Low risk, monitor situation
        - ⚪ **No Warning** - Safe conditions
        """)
    
    with col_map:
        st.subheader("🗺️ Landslide Warning Map")
        
        # Load landslide observations for point layer
        landslide_observations = load_landslide_observations_geojson()
        
        # Create and display map
        if st.session_state.landslide_data:
            m = create_landslide_choropleth_map(
                st.session_state.landslide_data, 
                districts_geojson,
                divisions_geojson,
                landslide_observations
            )
        else:
            m = create_empty_map("Landslide Warnings")
        
        components.html(m._repr_html_(), height=550)
        
        # Legend
        st.markdown(f"**Legend:** {get_landslide_legend_html()}", unsafe_allow_html=True)
        
        # Download GeoJSON button
        if st.session_state.landslide_data:
            # Create GeoJSON with landslide data
            geojson_export = copy.deepcopy(districts_geojson)
            landslide_lookup = {d["district"]: d for d in st.session_state.landslide_data.get("districts", [])}
            
            for feature in geojson_export["features"]:
                district_name = feature["properties"].get("district", "")
                if district_name in landslide_lookup:
                    feature["properties"].update(landslide_lookup[district_name])
            
            # Add metadata
            geojson_export["metadata"] = st.session_state.landslide_data.get("metadata", {})
            geojson_export["totals"] = st.session_state.landslide_data.get("totals", {})
            
            geojson_str = json.dumps(geojson_export, indent=2, ensure_ascii=False, default=str)
            
            # Generate filename with report date
            metadata = st.session_state.landslide_data.get("metadata", {})
            report_date = metadata.get("report_date", "")
            if report_date:
                try:
                    dt = datetime.fromisoformat(report_date)
                    date_suffix = dt.strftime("%Y-%m-%d_%H%M")
                except:
                    date_suffix = datetime.now().strftime("%Y-%m-%d_%H%M")
            else:
                date_suffix = datetime.now().strftime("%Y-%m-%d_%H%M")
            
            filename = f"landslide_warnings_{date_suffix}.geojson"
            
            st.download_button(
                label="📥 Download GeoJSON",
                data=geojson_str,
                file_name=filename,
                mime="application/geo+json",
            )
    
    # Landslide data table at bottom
    st.divider()
    with st.expander("📋 View All District Data", expanded=False):
        display_landslide_table(st.session_state.landslide_data)
