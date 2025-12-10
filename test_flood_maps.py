"""
Test script to generate flood maps with and without data.
"""
import json
from src.map_utils import create_flood_map

# Load GeoJSON files
with open("data/geo/rivers.geojson", "r") as f:
    rivers = json.load(f)

with open("data/geo/water_bodies.geojson", "r") as f:
    water_bodies = json.load(f)

# Test 1: Base map without flood data
print("Creating base map (no flood data)...")
m1 = create_flood_map(None, rivers, water_bodies)
m1.save("output/flood_map_base.html")
print("✅ Base map saved to: output/flood_map_base.html")

# Test 2: Map with flood data (alerts)
print("\nCreating map with flood data...")
with open("output/flood_data_test_with_alerts.json", "r") as f:
    flood_data = json.load(f)

# Count alerts
alert_count = 0
for basin_name, stations in flood_data["river_basins"].items():
    for station in stations:
        remarks = station.get("remarks")
        if remarks and remarks != "Normal":
            alert_count += 1
            print(f"  🟡 Alert: {station['tributary']} at {station['station']} - {remarks}")

print(f"\nTotal alerts: {alert_count}")

m2 = create_flood_map(flood_data, rivers, water_bodies)
m2.save("output/flood_map_with_alerts.html")
print("✅ Alert map saved to: output/flood_map_with_alerts.html")

print("\nDone! Open the HTML files in a browser to view the maps.")
