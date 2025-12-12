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
# COLOR FUNCTIONS - FLOOD
# ============================================================

FLOOD_ALERT_COLORS = {
    "Normal": "#28a745",  # Green
    "Alert": "#ffc107",   # Yellow
    "Minor Flood": "#fd7e14",  # Orange
    "Major Flood": "#dc3545",  # Red
    "default": "#6c757d"  # Gray for unknown
}

TREND_ICONS = {
    "Rising": "⬆️",
    "Falling": "⬇️",
    "Stable": "➡️",
    "default": "—"
}


def get_flood_alert_color(remarks: str | None) -> str:
    """Get color for flood alert status based on remarks field."""
    if not remarks or remarks == "-" or remarks == "Normal":
        return FLOOD_ALERT_COLORS["Normal"]
    return FLOOD_ALERT_COLORS.get(remarks, FLOOD_ALERT_COLORS["default"])


def get_trend_icon(trend: str | None) -> str:
    """Get icon for water level trend."""
    if not trend:
        return TREND_ICONS["default"]
    return TREND_ICONS.get(trend, TREND_ICONS["default"])


def create_flood_tooltip(station_data: dict) -> str:
    """Create HTML tooltip for flood monitoring station."""
    tributary = station_data.get("tributary", "Unknown")
    station = station_data.get("station", "Unknown")
    unit = station_data.get("unit", "m")
    alert_level = station_data.get("alert_level", "N/A")
    minor_flood = station_data.get("minor_flood_level", "N/A")
    major_flood = station_data.get("major_flood_level", "N/A")
    reading_1 = station_data.get("water_level_reading_1", "N/A")
    reading_2 = station_data.get("water_level_reading_2", "N/A")
    remarks = station_data.get("remarks") or "Normal"
    trend = station_data.get("water_level_trend")
    rainfall = station_data.get("rainfall_6hr_mm")
    
    trend_icon = get_trend_icon(trend)
    alert_color = get_flood_alert_color(remarks)
    
    # Format water level display
    if reading_2 not in [None, "N/A", "-"]:
        water_level_display = f"{reading_2} {unit}"
        if reading_1 not in [None, "N/A", "-"]:
            water_level_display += f" (prev: {reading_1} {unit})"
    elif reading_1 not in [None, "N/A", "-"]:
        water_level_display = f"{reading_1} {unit}"
    else:
        water_level_display = "No data"
    
    tooltip_html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; min-width: 200px;">
        <strong style="font-size: 14px;">{tributary}</strong><br>
        <span style="color: #666;">{station}</span><br>
        <hr style="margin: 5px 0;">
        <div style="background-color: {alert_color}; color: {'white' if remarks != 'Normal' else 'black'}; 
                    padding: 3px 8px; border-radius: 3px; margin: 5px 0; text-align: center; font-weight: bold;">
            {remarks}
        </div>
        <b>Water Level:</b> {water_level_display} {trend_icon}<br>
        <b>Alert Level:</b> {alert_level} {unit}<br>
        <b>Minor Flood:</b> {minor_flood} {unit}<br>
        <b>Major Flood:</b> {major_flood} {unit}<br>
    """
    
    if rainfall not in [None, "N/A", "-"]:
        tooltip_html += f"<b>6h Rainfall:</b> {rainfall} mm<br>"
    
    tooltip_html += "</div>"
    
    return tooltip_html


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
    districts_geojson: dict,
    divisions_geojson: dict | None = None,
    landslide_observations: dict | None = None
) -> folium.Map:
    """
    Create a choropleth map for landslide warning data.
    
    If divisions_geojson is provided, the map will show division-level coloring
    with district boundaries overlaid as a thicker stroke.
    Otherwise, falls back to district-level coloring.
    
    If landslide_observations is provided, adds point markers for observed landslides.
    """
    m = folium.Map(
        location=[7.8731, 80.7718],
        zoom_start=7,
        tiles="cartodbpositron"
    )
    
    if not landslide_data:
        return create_empty_map("Landslide Warnings")
    
    # Build division-level lookup from landslide data
    from src.landslide_extractor import build_division_lookup, normalize_division_name
    division_lookup = build_division_lookup(landslide_data)
    
    # If we have divisions GeoJSON, render divisions with district overlay
    if divisions_geojson:
        # First, add division polygons (colored by warning level)
        for feature in divisions_geojson.get("features", []):
            division_name = feature["properties"].get("shapeName", "Unknown")
            
            # Try to match division name with our lookup
            norm_name = normalize_division_name(division_name)
            
            # Try exact match first, then partial matching
            matched_data = None
            if norm_name in division_lookup:
                matched_data = division_lookup[norm_name]
            else:
                # Try partial match - check if any lookup key is contained in norm_name or vice versa
                for lookup_key, data in division_lookup.items():
                    lookup_norm = normalize_division_name(lookup_key)
                    if lookup_norm in norm_name or norm_name in lookup_norm:
                        matched_data = data
                        break
            
            if matched_data:
                level = matched_data["level"]
                district = matched_data["district"]
            else:
                level = 0
                district = "Unknown"
            
            color = get_landslide_color(level)
            level_name = {0: "No Warning", 1: "Yellow", 2: "Amber", 3: "Red"}.get(level, "Unknown")
            level_emoji = {0: "⚪", 1: "🟡", 2: "🟠", 3: "🔴"}.get(level, "⚪")
            
            tooltip_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 12px; width: 250px;">
                <strong style="font-size: 14px;">{division_name}</strong><br>
                <span style="color: #666;">District: {district}</span><br>
                <hr style="margin: 5px 0;">
                <span>{level_emoji} Alert Level: <b>{level_name}</b></span>
            </div>
            """
            
            folium.GeoJson(
                feature,
                style_function=lambda x, c=color: {
                    "fillColor": c,
                    "color": "#666",
                    "weight": 0.5,
                    "fillOpacity": 0.7
                },
                tooltip=folium.Tooltip(tooltip_html, sticky=True),
            ).add_to(m)
        
        # Then, add district boundaries as overlay (thicker stroke, no fill, non-interactive)
        for feature in districts_geojson.get("features", []):
            folium.GeoJson(
                feature,
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "fillOpacity": 0,
                    "color": "#333",
                    "weight": 2.5,
                    "interactive": False,
                },
                interactive=False,
            ).add_to(m)
    else:
        # Fallback: district-level coloring (original behavior)
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
    
    # Add landslide observations as point markers if available
    if landslide_observations:
        for feature in landslide_observations.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            
            if geom.get("type") != "Point":
                continue
            
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            
            lon, lat = coords[0], coords[1]
            obs_type = props.get("Type", "Unknown")
            obs_name = props.get("Name", "").strip()
            
            # Determine marker color and icon based on observation type
            if "Landslide observed" in obs_type:
                marker_color = "red"
                icon_name = "exclamation-triangle"
                obs_status = "⚠️ Landslide Observed"
            elif "No landslides observed" in obs_type:
                marker_color = "green"
                icon_name = "check"
                obs_status = "✅ No Landslide Observed"
            elif "cloud cover" in obs_type.lower():
                marker_color = "gray"
                icon_name = "cloud"
                obs_status = "☁️ N/A (Cloud Cover)"
            else:
                marker_color = "blue"
                icon_name = "info"
                obs_status = obs_type
            
            # Find which division this point is in (using division lookup for context)
            # For now, just show the observation info
            tooltip_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 12px; width: 220px;">
                <strong style="font-size: 13px;">📍 Landslide Observation</strong><br>
                <hr style="margin: 5px 0;">
                <b>Status:</b> {obs_status}<br>
                <b>Source:</b> {obs_name if obs_name else 'LHMP-LRRMD'}<br>
                <b>Location:</b> {lat:.4f}°N, {lon:.4f}°E
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                tooltip=folium.Tooltip(tooltip_html, sticky=True),
                icon=folium.Icon(color=marker_color, icon=icon_name, prefix='fa')
            ).add_to(m)
    
    return m


def create_flood_map(
    flood_data: dict | None,
    rivers_geojson: dict,
    water_bodies_geojson: dict | None = None
) -> folium.Map:
    """Create a map for flood warnings showing monitored rivers.
    
    Uses the standard_name property from monitored_rivers.geojson to match with flood data.
    """
    m = folium.Map(
        location=[7.8731, 80.7718],
        zoom_start=7,
        tiles="cartodbpositron"
    )
    
    # Build station lookup from flood data using tributary names
    station_lookup = {}
    if flood_data:
        for basin_name, stations in flood_data.get("river_basins", {}).items():
            for station in stations:
                tributary = station.get("tributary", "").strip()
                if tributary:
                    tributary_lower = tributary.lower()
                    station_lookup[tributary_lower] = station
    
    # Add rivers layer - all rivers from monitored_rivers.geojson
    for feature in rivers_geojson.get("features", []):
        # Use standard_name for matching with scraped data
        standard_name = feature["properties"].get("standard_name")
        river_name = feature["properties"].get("name")
        
        if not standard_name:
            continue
        
        # Look up station data using standard_name
        station_data = station_lookup.get(standard_name.lower())
        
        if station_data:
            # River has monitoring data - color by alert status
            remarks = station_data.get("remarks") or "Normal"
            color = get_flood_alert_color(remarks)
            weight = 3 if remarks not in ["Normal", None] else 2
            opacity = 0.9 if remarks not in ["Normal", None] else 0.6
            
            tooltip_html = create_flood_tooltip(station_data)
        else:
            # Show river without data in default color
            color = FLOOD_ALERT_COLORS["Normal"]
            weight = 2
            opacity = 0.6
            tooltip_html = f"<b>{river_name or standard_name}</b><br>No current monitoring data"
        
        folium.GeoJson(
            feature,
            style_function=lambda x, c=color, w=weight, o=opacity: {
                "color": c,
                "weight": w,
                "opacity": o
            },
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)
    
    # Add legend only when flood data is available
    if flood_data:
        legend_html = f"""
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; border-radius: 5px;">
            <h4 style="margin-top: 0;">Flood Alert Status</h4>
            <div style="margin: 5px 0;">
                <span style="background-color: {FLOOD_ALERT_COLORS['Normal']}; width: 20px; height: 3px; 
                             display: inline-block; margin-right: 5px;"></span> Normal
            </div>
            <div style="margin: 5px 0;">
                <span style="background-color: {FLOOD_ALERT_COLORS['Alert']}; width: 20px; height: 3px; 
                             display: inline-block; margin-right: 5px;"></span> Alert
            </div>
            <div style="margin: 5px 0;">
                <span style="background-color: {FLOOD_ALERT_COLORS['Minor Flood']}; width: 20px; height: 3px; 
                             display: inline-block; margin-right: 5px;"></span> Minor Flood
            </div>
            <div style="margin: 5px 0;">
                <span style="background-color: {FLOOD_ALERT_COLORS['Major Flood']}; width: 20px; height: 3px; 
                             display: inline-block; margin-right: 5px;"></span> Major Flood
            </div>
            <hr style="margin: 10px 0;">
            <div style="font-size: 12px; color: #666;">
                ⬆️ Rising | ⬇️ Falling | ➡️ Stable
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
    
    return m
