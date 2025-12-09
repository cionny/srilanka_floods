"""
Flood Warnings tab for the Sri Lanka Monitoring Dashboard.
Placeholder for future flood warning functionality.
"""

import streamlit as st
import streamlit.components.v1 as components

from src.data_manager import DMC_URLS
from src.map_utils import create_empty_map


# ============================================================
# TAB RENDER FUNCTION
# ============================================================

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
