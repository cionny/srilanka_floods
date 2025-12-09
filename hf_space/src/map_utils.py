"""
Map creation utilities for the Sri Lanka Monitoring Dashboard.
Handles Folium choropleth maps, color schemes, and legends.
"""

import folium

# ============================================================
# METRIC CONFIGURATION
# ============================================================

# Consistent color palette for all sitrep metrics (red gradient)
SITREP_COLORS = ['#f7f7f7', '#fef0d9', '#fdcc8a', '#fc8d59', '#e34a33', '#b30000', '#7f0000']

METRIC_CONFIG = {
    "people_affected": {
        "label": "People Affected",
        "thresholds": [1, 10000, 50000, 100000, 200000, 350000],
        "format": lambda x: f"{x:,}"
    },
    "people_displaced": {
        "label": "People Displaced",
        "thresholds": [1, 500, 2000, 5000, 10000, 20000],
        "format": lambda x: f"{x:,}"
    },
    "deaths": {
        "label": "Deaths",
        "thresholds": [1, 10, 25, 50, 75, 100],
        "format": lambda x: str(x)
    },
    "missing": {
        "label": "Missing Persons",
        "thresholds": [1, 5, 10, 20, 30, 50],
        "format": lambda x: str(x)
    },
    "houses_fully_damaged": {
        "label": "Houses Fully Damaged",
        "thresholds": [1, 50, 100, 250, 400, 500],
        "format": lambda x: f"{x:,}"
    },
    "houses_partially_damaged": {
        "label": "Houses Partially Damaged",
        "thresholds": [1, 500, 2000, 5000, 7500, 10000],
        "format": lambda x: f"{x:,}"
    }
}


# ============================================================
# COLOR FUNCTIONS - SITREP
# ============================================================

def get_color_for_metric(value: int, metric: str) -> str:
    """Get color for a value based on the metric's thresholds using consistent palette."""
    config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    thresholds = config["thresholds"]
    
    if value == 0:
        return SITREP_COLORS[0]  # Light gray for 0
    
    for i, threshold in enumerate(thresholds):
        if value < threshold:
            return SITREP_COLORS[i]
    return SITREP_COLORS[-1]  # Highest color for values above all thresholds


def get_color(value: int, metric: str) -> str:
    """Alias for get_color_for_metric for backwards compatibility."""
    return get_color_for_metric(value, metric)


def get_legend_html(metric: str) -> str:
    """Generate HTML legend for the selected metric with consistent colors."""
    config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    thresholds = config["thresholds"]
    colors = SITREP_COLORS
    
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
# COLOR FUNCTIONS - LANDSLIDE
# ============================================================

LANDSLIDE_COLORS = {
    0: "#f0f0f0",  # No warning - light gray
    1: "#ffeb3b",  # Level 1 - Yellow
    2: "#ff9800",  # Level 2 - Amber/Orange
    3: "#f44336",  # Level 3 - Red
}


def get_landslide_color(level: int) -> str:
    """Get color for landslide warning level."""
    return LANDSLIDE_COLORS.get(level, LANDSLIDE_COLORS[0])


def get_landslide_legend_html() -> str:
    """Generate legend HTML for landslide warning levels."""
    return (
        '<span style="background-color: #f0f0f0; padding: 2px 8px; margin: 2px; border-radius: 3px;">No Warning</span> '
        '<span style="background-color: #ffeb3b; padding: 2px 8px; margin: 2px; border-radius: 3px;">🟡 Level 1</span> '
        '<span style="background-color: #ff9800; padding: 2px 8px; margin: 2px; border-radius: 3px;">🟠 Level 2</span> '
        '<span style="background-color: #f44336; color: white; padding: 2px 8px; margin: 2px; border-radius: 3px;">🔴 Level 3</span>'
    )


# ============================================================
# MAP CREATION FUNCTIONS
# ============================================================

def create_empty_map(title: str = "Map") -> folium.Map:
    """Create an empty map centered on Sri Lanka."""
    m = folium.Map(
        location=[7.8731, 80.7718],
        zoom_start=7,
        tiles="cartodbpositron"
    )
    folium.map.Marker(
        [7.8731, 80.7718],
        icon=folium.DivIcon(
            html=f'<div style="font-size: 12px; color: #666; text-align: center;">{title}<br>No data loaded</div>'
        )
    ).add_to(m)
    return m


def create_choropleth_map(
    sitrep_data: dict | None, 
    districts_geojson: dict, 
    metric: str = "people_affected"
) -> folium.Map:
    """Create a choropleth map for situation report data."""
    m = folium.Map(
        location=[7.8731, 80.7718],
        zoom_start=7,
        tiles="cartodbpositron"
    )
    
    if not sitrep_data:
        return create_empty_map("Situation Report")
    
    # Build lookup from sitrep data
    district_data = {d["district"]: d for d in sitrep_data.get("districts", [])}
    config = METRIC_CONFIG.get(metric, METRIC_CONFIG["people_affected"])
    format_fn = config["format"]
    
    for feature in districts_geojson.get("features", []):
        district_name = feature["properties"].get("district", "Unknown")
        data = district_data.get(district_name, {})
        value = data.get(metric, 0) if data else 0
        
        color = get_color_for_metric(value, metric)
        
        # Build tooltip
        tooltip_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px; min-width: 150px;">
            <strong style="font-size: 14px;">{district_name}</strong><br>
            <hr style="margin: 5px 0;">
            <b>{config['label']}:</b> {format_fn(value)}<br>
            <b>People Affected:</b> {data.get('people_affected', 0):,}<br>
            <b>People Displaced:</b> {data.get('people_displaced', 0):,}<br>
            <b>Deaths:</b> {data.get('deaths', 0)}<br>
            <b>Missing:</b> {data.get('missing', 0)}<br>
            <b>Houses Fully Damaged:</b> {data.get('houses_fully_damaged', 0):,}<br>
            <b>Houses Partially Damaged:</b> {data.get('houses_partially_damaged', 0):,}
        </div>
        """
        
        folium.GeoJson(
            feature,
            style_function=lambda x, c=color: {
                "fillColor": c,
                "color": "#333",
                "weight": 1,
                "fillOpacity": 0.7
            },
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)
    
    return m


def create_landslide_choropleth_map(
    landslide_data: dict | None,
    districts_geojson: dict
) -> folium.Map:
    """Create a choropleth map for landslide warning data."""
    m = folium.Map(
        location=[7.8731, 80.7718],
        zoom_start=7,
        tiles="cartodbpositron"
    )
    
    if not landslide_data:
        return create_empty_map("Landslide Warnings")
    
    # Build lookup from landslide data
    district_data = {d["district"]: d for d in landslide_data.get("districts", [])}
    
    for feature in districts_geojson.get("features", []):
        district_name = feature["properties"].get("district", "Unknown")
        data = district_data.get(district_name, {})
        max_level = data.get("max_level", 0) if data else 0
        
        color = get_landslide_color(max_level)
        
        # Build tooltip with division details
        level_3_divs = data.get("level_3_divisions", [])
        level_2_divs = data.get("level_2_divisions", [])
        level_1_divs = data.get("level_1_divisions", [])
        total_warnings = data.get("total_warnings", 0)
        
        level_name = {0: "No Warning", 1: "Yellow", 2: "Amber", 3: "Red"}.get(max_level, "Unknown")
        level_emoji = {0: "⚪", 1: "🟡", 2: "🟠", 3: "🔴"}.get(max_level, "⚪")
        
        # Format division lists with truncation
        def format_divisions(divs: list, max_show: int = 3) -> str:
            if not divs:
                return "None"
            if len(divs) <= max_show:
                return ", ".join(divs)
            return ", ".join(divs[:max_show]) + f" (+{len(divs) - max_show} more)"
        
        tooltip_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px; width: 280px;">
            <strong style="font-size: 14px;">{district_name}</strong><br>
            <span>{level_emoji} Alert Level: <b>{level_name}</b></span><br>
            <hr style="margin: 5px 0;">
            <b>Total Divisions with Warnings:</b> {total_warnings}<br>
            <b>🔴 Level 3 (Red):</b> {format_divisions(level_3_divs)}<br>
            <b>🟠 Level 2 (Amber):</b> {format_divisions(level_2_divs)}<br>
            <b>🟡 Level 1 (Yellow):</b> {format_divisions(level_1_divs)}
        </div>
        """
        
        folium.GeoJson(
            feature,
            style_function=lambda x, c=color: {
                "fillColor": c,
                "color": "#333",
                "weight": 1,
                "fillOpacity": 0.7
            },
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)
    
    return m
