"""
Flask web server for the Sri Lanka Flood Situation Map.

Serves an interactive map with disaster data from DMC situation reports.
"""

from flask import Flask, render_template, jsonify, send_from_directory
from pathlib import Path
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import pipeline components
from scraper import get_latest_sitrep, download_pdf
from pdf_extractor import extract_sitrep_data, convert_to_geojson, save_to_json

app = Flask(__name__, template_folder='../templates', static_folder='../output')

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
GEOJSON_PATH = OUTPUT_DIR / "sitrep_data.geojson"
JSON_PATH = OUTPUT_DIR / "extracted_data.json"


def load_geojson_data() -> dict | None:
    """Load cached GeoJSON data from file."""
    if GEOJSON_PATH.exists():
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def fetch_and_extract_data() -> dict:
    """
    Run the full pipeline: scrape, download, extract, and save data.
    
    Returns:
        GeoJSON data dictionary
    """
    print("Fetching latest sitrep from DMC...")
    sitrep = get_latest_sitrep()
    
    if not sitrep:
        raise ValueError("Could not find any situation reports on DMC website")
    
    print(f"Downloading PDF: {sitrep['pdf_url']}")
    pdf_bytes = download_pdf(sitrep['pdf_url'])
    
    print("Extracting data from PDF...")
    data = extract_sitrep_data(pdf_bytes)
    data["metadata"]["pdf_url"] = sitrep["pdf_url"]
    data["metadata"]["scraped_title"] = sitrep.get("title", "")
    
    # Save extracted data
    save_to_json(data, JSON_PATH)
    
    # Convert to GeoJSON and save
    geojson_data = convert_to_geojson(data)
    save_to_json(geojson_data, GEOJSON_PATH)
    
    print("Data extraction complete!")
    return geojson_data


@app.route('/')
def index():
    """Serve the main map page."""
    data = load_geojson_data()
    
    # Get report link from cached data
    report_link = ""
    if data and "metadata" in data:
        report_link = data["metadata"].get("pdf_url", "")
    
    return render_template('map_template.html', report_link=report_link)


@app.route('/api/data')
def get_data():
    """API endpoint to get the current GeoJSON data."""
    data = load_geojson_data()
    if data:
        return jsonify(data)
    return jsonify({"error": "No data available. Click 'Update Data' to fetch."}), 404


@app.route('/api/update', methods=['POST'])
def update_data():
    """API endpoint to trigger data refresh from DMC website."""
    try:
        data = fetch_and_extract_data()
        return jsonify({
            "success": True,
            "message": "Data updated successfully",
            "totals": data.get("totals", {}),
            "metadata": data.get("metadata", {})
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/output/<path:filename>')
def serve_output(filename):
    """Serve files from the output directory."""
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == '__main__':
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Run the Flask development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"Starting server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)