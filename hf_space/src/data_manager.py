"""
Data loading and saving functions for the Sri Lanka Monitoring Dashboard.
Handles file I/O for sitreps, landslide data, and district GeoJSON.
"""

import json
from pathlib import Path
from datetime import datetime

# ============================================================
# PATH CONFIGURATION
# ============================================================

# Determine if running in HF Space or locally
if Path("/home/user/app").exists():
    BASE_DIR = Path("/home/user/app")
else:
    BASE_DIR = Path(__file__).parent.parent

DATA_DIR = BASE_DIR / "data"
SITREPS_DIR = DATA_DIR / "sitreps"
LANDSLIDE_DIR = DATA_DIR / "landslide"
DISTRICTS_GEOJSON = DATA_DIR / "districts.geojson"

# DMC URLs
DMC_URLS = {
    "sitrep": "https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=273&report_type_id=1&lang=en",
    "landslide": "https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en",
    "flood": "https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en",
    "weather": "https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=274&report_type_id=2&lang=en"
}


# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

def load_districts_geojson() -> dict:
    """Load the districts GeoJSON file."""
    if DISTRICTS_GEOJSON.exists():
        with open(DISTRICTS_GEOJSON, "r") as f:
            return json.load(f)
    raise FileNotFoundError(f"Districts GeoJSON not found at {DISTRICTS_GEOJSON}")


def load_latest_data() -> dict | None:
    """Load the latest sitrep data if available."""
    latest_file = SITREPS_DIR / "latest.json"
    if latest_file.exists():
        with open(latest_file, "r") as f:
            return json.load(f)
    return None


def load_previous_data() -> dict | None:
    """Load the previous sitrep data if available."""
    previous_file = SITREPS_DIR / "previous.json"
    if previous_file.exists():
        with open(previous_file, "r") as f:
            return json.load(f)
    return None


def load_landslide_data() -> dict | None:
    """Load the latest landslide data if available."""
    latest_file = LANDSLIDE_DIR / "latest.json"
    if latest_file.exists():
        with open(latest_file, "r") as f:
            return json.load(f)
    return None


# ============================================================
# DATA SAVING FUNCTIONS
# ============================================================

def save_data(data: dict, filename: str) -> Path:
    """Save sitrep data to a JSON file in the sitreps directory."""
    SITREPS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SITREPS_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return filepath


def save_landslide_data(data: dict, filename: str) -> Path:
    """Save landslide data to a JSON file in the landslide directory."""
    LANDSLIDE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = LANDSLIDE_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return filepath


# ============================================================
# DATA FETCHING FUNCTIONS
# ============================================================

def fetch_and_extract_data() -> tuple[dict, dict | None]:
    """
    Fetch and extract the latest and previous sitrep data from DMC.
    
    Returns:
        Tuple of (latest_data, previous_data)
    """
    # Import here to avoid circular imports
    from src.scraper import get_sitrep_list, download_pdf
    from src.pdf_extractor import extract_sitrep_data
    
    reports = get_sitrep_list(limit=2)
    if not reports:
        raise ValueError("No situation reports found on DMC website")
    
    # Get latest report
    latest_report = reports[0]
    pdf_bytes = download_pdf(latest_report["pdf_url"])
    latest_data = extract_sitrep_data(pdf_bytes)
    latest_data["metadata"]["pdf_url"] = latest_report["pdf_url"]
    latest_data["metadata"]["scraped_title"] = latest_report.get("title", "")
    
    # Get previous report if available
    previous_data = None
    if len(reports) > 1:
        prev_report = reports[1]
        try:
            prev_pdf_bytes = download_pdf(prev_report["pdf_url"])
            previous_data = extract_sitrep_data(prev_pdf_bytes)
            previous_data["metadata"]["pdf_url"] = prev_report["pdf_url"]
            previous_data["metadata"]["scraped_title"] = prev_report.get("title", "")
        except Exception:
            pass  # Previous report is optional
    
    return latest_data, previous_data
