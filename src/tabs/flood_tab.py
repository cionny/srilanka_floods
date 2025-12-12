"""
Flood Warnings tab for the Sri Lanka Monitoring Dashboard.
Displays water level and rainfall data for river monitoring stations.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
from pathlib import Path
import pandas as pd

from src.data_manager import DMC_URLS, load_geojson, load_flood_data
from src.map_utils import create_flood_map, create_empty_map


# ============================================================
# DISPLAY HELPER FUNCTIONS
# ============================================================

def display_flood_station_table(flood_data: dict | None):
    """Display a table with all flood monitoring station data."""
    if not flood_data:
        st.info("No flood data available")
        return
    
    all_stations = flood_data.get("all_stations", [])
    if not all_stations:
        # Build from river_basins if all_stations not available
        all_stations = []
        for basin_name, stations in flood_data.get("river_basins", {}).items():
            for station in stations:
                station_copy = station.copy()
                station_copy["river_basin"] = basin_name
                all_stations.append(station_copy)
    
    if not all_stations:
        st.info("No station data available")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_stations)
    
    # Select and order columns
    column_order = ["river_basin", "tributary", "station", "water_level_reading_2", "unit", 
                    "alert_level", "minor_flood_level", "major_flood_level", "remarks", "rainfall_6hr_mm"]
    available_cols = [c for c in column_order if c in df.columns]
    df = df[available_cols]
    
    # Rename columns for display
    column_rename = {
        "river_basin": "River Basin",
        "tributary": "Tributary",
        "station": "Station",
        "water_level_reading_2": "Water Level",
        "unit": "Unit",
        "alert_level": "Alert Level",
        "minor_flood_level": "Minor Flood",
        "major_flood_level": "Major Flood",
        "remarks": "Status",
        "rainfall_6hr_mm": "Rainfall (6hr mm)"
    }
    df = df.rename(columns=column_rename)
    
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# TAB RENDER FUNCTION
# ============================================================

def render_flood_tab(districts_geojson: dict):
    """Render the Flood Warnings tab."""
    st.header("🌊 Flood & Water Level Monitoring")
    st.markdown(f"""
    Real-time river water levels and flood warnings from DMC.  
    **Source:** [DMC Flood Reports]({DMC_URLS['flood']})
    """)
    
    # Refresh button
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refresh Flood Data", use_container_width=True, type="primary"):
            with st.spinner("Fetching latest flood data..."):
                from src.flood_extractor import scrape_and_save_latest
                try:
                    flood_data = scrape_and_save_latest()
                    st.session_state.flood_data = flood_data
                    st.success("✅ Flood data updated successfully!")
                except Exception as e:
                    st.error(f"❌ Error fetching flood data: {e}")
                    st.session_state.flood_data = None
    
    with col_info:
        flood_data = load_flood_data()
        if flood_data and flood_data.get("metadata"):
            metadata = flood_data["metadata"]
            report_date = metadata.get("report_date_formatted", "Unknown")
            report_time = metadata.get("report_time", "")
            st.info(f"📅 **Last Updated:** {report_date} at {report_time}")
            if "pdf_url" in metadata:
                st.markdown(f"[📄 View Original PDF]({metadata['pdf_url']})")
        else:
            st.warning("No flood data loaded. Click refresh to fetch latest data.")
    
    st.divider()
    
    # Load GeoJSON data for monitored rivers
    monitored_rivers_geojson = load_geojson("data/geo/monitored_rivers.geojson")
    
    # Create map
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ River Monitoring Map")
        
        if monitored_rivers_geojson:
            m = create_flood_map(flood_data, monitored_rivers_geojson, None)
            components.html(m._repr_html_(), height=600)
            if flood_data:
                st.caption("Rivers are color-coded by alert status. Hover over rivers to see detailed station information.")
            else:
                st.caption("Showing monitored rivers. Click 'Refresh' to load flood monitoring data.")
        else:
            m = create_empty_map("River Monitoring")
            components.html(m._repr_html_(), height=600)
            st.caption("🚧 GeoJSON data not available")
    
    with col2:
        st.subheader("⚠️ Active Alerts")
        
        if flood_data:
            # Count alerts by status
            alert_counts = {"Normal": 0, "Alert": 0, "Minor Flood": 0, "Major Flood": 0}
            stations_with_alerts = []
            
            for basin_name, stations in flood_data.get("river_basins", {}).items():
                for station in stations:
                    remarks = station.get("remarks") or "Normal"
                    if remarks in alert_counts:
                        alert_counts[remarks] += 1
                    
                    if remarks and remarks != "Normal":
                        stations_with_alerts.append({
                            "basin": basin_name,
                            "tributary": station.get("tributary"),
                            "station": station.get("station"),
                            "status": remarks,
                            "water_level": station.get("water_level_reading_2") or station.get("water_level_reading_1"),
                            "unit": station.get("unit", "m"),
                            "trend": station.get("water_level_trend")
                        })
            
            # Display alert summary
            col_alert1, col_alert2 = st.columns(2)
            with col_alert1:
                if alert_counts["Major Flood"] > 0:
                    st.metric("🔴 Major Flood", alert_counts["Major Flood"])
                if alert_counts["Minor Flood"] > 0:
                    st.metric("🟠 Minor Flood", alert_counts["Minor Flood"])
            with col_alert2:
                if alert_counts["Alert"] > 0:
                    st.metric("🟡 Alert", alert_counts["Alert"])
                st.metric("🟢 Normal", alert_counts["Normal"])
            
            st.divider()
            
            # Show stations with alerts
            if stations_with_alerts:
                st.markdown("**Active Alert Stations:**")
                for alert_station in stations_with_alerts:
                    status_emoji = {
                        "Alert": "🟡",
                        "Minor Flood": "🟠",
                        "Major Flood": "🔴"
                    }.get(alert_station["status"], "⚪")
                    
                    trend_emoji = {
                        "Rising": "⬆️",
                        "Falling": "⬇️",
                        "Stable": "➡️"
                    }.get(alert_station["trend"], "")
                    
                    st.markdown(f"""
                    {status_emoji} **{alert_station['tributary']}** - {alert_station['station']}  
                    Water Level: {alert_station['water_level']} {alert_station['unit']} {trend_emoji}
                    """)
            else:
                st.success("✅ No active alerts. All stations normal.")
        else:
            st.info("""
            **Water Level Monitoring:**
            - Real-time water levels at gauging stations
            - Alert levels and flood thresholds
            - Water level trends (Rising/Falling/Stable)
            - 6-hour rainfall data
            """)
        
        st.divider()
        
        st.subheader("📊 Alert Levels")
        st.markdown("""
        - 🔴 **Major Flood** - Severe flooding
        - 🟠 **Minor Flood** - Flooding in progress
        - 🟡 **Alert** - Water at alert level
        - 🟢 **Normal** - Safe water levels
        
        **Trends:**
        - ⬆️ Rising - Water level increasing
        - ⬇️ Falling - Water level decreasing
        - ➡️ Stable - Water level steady
        """)
    
    # Station data table at bottom
    st.divider()
    with st.expander("📋 View All Station Data", expanded=False):
        display_flood_station_table(flood_data)
