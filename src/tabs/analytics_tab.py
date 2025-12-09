"""
Dynamic Analytical Brief tab for the Sri Lanka Disaster Dashboard.

Provides AI-powered trend analysis using LLM (DeepSeek/OpenAI).
"""

import streamlit as st
from datetime import datetime
from pathlib import Path


def render_analytics_tab(sitreps_dir: Path, generate_trend_summary_func):
    """
    Render the Dynamic Analytical Brief tab with AI-powered analysis.
    
    Args:
        sitreps_dir: Path to the sitreps data directory
        generate_trend_summary_func: Function to call for generating trend summary
    """
    st.header("🤖 Dynamic Analytical Brief")
    st.markdown("""
    AI-powered analysis of disaster trends and patterns across all available situation reports.
    The system analyzes historical data to identify priority areas, emerging patterns, and provides
    operational recommendations.
    """)
    
    st.divider()
    
    # Initialize session state for trend summary
    if "trend_summary" not in st.session_state:
        st.session_state.trend_summary = None
    if "trend_summary_error" not in st.session_state:
        st.session_state.trend_summary_error = None
    
    # Controls section
    col_btn, col_warning = st.columns([1, 3])
    
    with col_btn:
        generate_clicked = st.button(
            "🤖 Generate AI Analysis",
            use_container_width=True,
            type="primary",
            help="Generates a comprehensive trend analysis using AI"
        )
    
    with col_warning:
        st.info(
            "⚠️ **Please use responsibly:** Only regenerate after several new situation reports "
            "have been published to avoid unnecessary API usage."
        )
    
    if generate_clicked:
        with st.spinner("🔄 Analyzing trends across all situation reports..."):
            result = generate_trend_summary_func(sitreps_dir)
            
            if result["success"]:
                st.session_state.trend_summary = result["summary"]
                st.session_state.trend_summary_meta = {
                    "provider": result.get("provider", "Unknown"),
                    "num_reports": result.get("num_reports", 0),
                    "date_range": result.get("date_range", {}),
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.session_state.trend_summary_error = None
            else:
                st.session_state.trend_summary = None
                st.session_state.trend_summary_error = result.get("error", "Unknown error occurred")
    
    st.divider()
    
    # Display the summary or placeholder
    if st.session_state.trend_summary:
        meta = st.session_state.get("trend_summary_meta", {})
        
        # Metadata row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("AI Provider", meta.get('provider', 'Unknown'))
        with col2:
            st.metric("Reports Analyzed", meta.get('num_reports', '?'))
        with col3:
            st.metric("Generated At", meta.get('generated_at', 'Unknown'))
        
        st.divider()
        
        # Display the summary in a styled container
        st.subheader("📋 Analysis Report")
        with st.container():
            st.markdown(st.session_state.trend_summary)
    
    elif st.session_state.trend_summary_error:
        st.error(f"❌ {st.session_state.trend_summary_error}")
    
    else:
        # Placeholder when no analysis has been generated
        st.markdown(
            """
            <div style="padding: 40px; background-color: #f0f2f6; border-radius: 10px; text-align: center; margin-top: 20px;">
                <h3 style="color: #333; margin-bottom: 10px;">📊 No Analysis Generated Yet</h3>
                <p style="color: #666; margin: 0;">
                    Click <strong>"Generate AI Analysis"</strong> above to analyze trends across all available situation reports.
                </p>
                <p style="color: #888; font-size: 14px; margin-top: 15px;">
                    The AI will identify:
                </p>
                <ul style="color: #888; font-size: 14px; text-align: left; display: inline-block;">
                    <li>Priority districts requiring immediate attention</li>
                    <li>Emerging patterns and trends</li>
                    <li>Comparative analysis between reports</li>
                    <li>Operational recommendations</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Data sources info
    st.divider()
    with st.expander("ℹ️ About This Analysis"):
        st.markdown("""
        ### How It Works
        
        1. **Data Collection**: All available situation reports are loaded from the `data/sitreps` directory
        2. **Preprocessing**: Reports are parsed and key metrics are extracted (deaths, missing, displaced, etc.)
        3. **AI Analysis**: The data is sent to an LLM (DeepSeek or OpenAI) for comprehensive analysis
        4. **Report Generation**: The AI generates insights, identifies patterns, and provides recommendations
        
        ### Data Sources
        - **Situation Reports**: Official DMC situation reports (PDF extracted)
        - **Update Frequency**: Analysis should be regenerated after new reports are published
        
        ### AI Providers
        - **Primary**: DeepSeek AI (cost-effective, high quality)
        - **Fallback**: OpenAI GPT-4 (if DeepSeek is unavailable)
        """)
