"""
PDF Extractor for Sri Lanka DMC Situation Reports.

Extracts structured data from PDF situation reports using PyMuPDF.
No VLM required - uses direct text and table extraction.
"""

import fitz  # PyMuPDF
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


# District coordinates for map visualization (approximate centroids)
DISTRICT_COORDS = {
    "Ampara": {"lat": 7.2917, "lon": 81.6720},
    "Anuradhapura": {"lat": 8.3350, "lon": 80.4108},
    "Badulla": {"lat": 6.9934, "lon": 81.0550},
    "Batticaloa": {"lat": 7.7310, "lon": 81.6747},
    "Colombo": {"lat": 6.9271, "lon": 79.8612},
    "Galle": {"lat": 6.0535, "lon": 80.2210},
    "Gampaha": {"lat": 7.0873, "lon": 80.0144},
    "Hambantota": {"lat": 6.1429, "lon": 81.1212},
    "Jaffna": {"lat": 9.6615, "lon": 80.0255},
    "Kalutara": {"lat": 6.5854, "lon": 79.9607},
    "Kandy": {"lat": 7.2906, "lon": 80.6337},
    "Kegalle": {"lat": 7.2513, "lon": 80.3464},
    "Kilinochchi": {"lat": 9.3803, "lon": 80.3770},
    "Kurunegala": {"lat": 7.4863, "lon": 80.3647},
    "Mannar": {"lat": 8.9810, "lon": 79.9044},
    "Matale": {"lat": 7.4675, "lon": 80.6234},
    "Matara": {"lat": 5.9549, "lon": 80.5550},
    "Monaragala": {"lat": 6.8728, "lon": 81.3507},
    "Mullaitivu": {"lat": 9.2671, "lon": 80.8142},
    "Nuwara Eliya": {"lat": 6.9497, "lon": 80.7891},
    "Polonnaruwa": {"lat": 7.9403, "lon": 81.0188},
    "Puttalam": {"lat": 8.0362, "lon": 79.8283},
    "Ratnapura": {"lat": 6.6828, "lon": 80.3992},
    "Rathnapura": {"lat": 6.6828, "lon": 80.3992},  # Alternative spelling
    "Trincomalee": {"lat": 8.5874, "lon": 81.2152},
    "Vavuniya": {"lat": 8.7514, "lon": 80.4971},
}


def extract_metadata_from_text(text: str) -> dict:
    """Extract report metadata from PDF text."""
    metadata = {
        "source": "Disaster Management Center, Sri Lanka",
        "extracted_at": datetime.now().isoformat(),
    }
    
    # Extract date and time from report header
    # Pattern: "Situation Report on 2025.12.07 at 1200 hrs"
    date_pattern = r"Situation Report on (\d{4}\.\d{2}\.\d{2}) at (\d{4}) hrs"
    match = re.search(date_pattern, text)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        try:
            report_date = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H%M")
            metadata["report_date"] = report_date.isoformat()
            metadata["report_date_formatted"] = report_date.strftime("%B %d, %Y at %H:%M hrs")
        except ValueError:
            metadata["report_date_raw"] = f"{date_str} {time_str}"
    else:
        metadata["report_date_raw"] = "Unknown"
    
    # Extract signatory information
    signatory_pattern = r"([A-Z]\.[A-Z]\.[A-Z]\.?\s+\w+)\s*\n\s*(Deputy Director|Director)"
    match = re.search(signatory_pattern, text)
    if match:
        metadata["signatory"] = match.group(1).strip()
        metadata["signatory_title"] = match.group(2).strip()
    
    return metadata


def clean_numeric_value(value: str) -> int:
    """Convert string value to integer, handling commas and dashes."""
    if value is None or value == "-" or value == "" or pd.isna(value):
        return 0
    # Remove commas and convert to int
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def normalize_district_name(name: str) -> str:
    """Normalize district name for consistency."""
    if name is None or pd.isna(name):
        return ""
    name = str(name).strip()
    # Handle alternative spellings
    if name == "Rathnapura":
        return "Ratnapura"
    return name


def extract_table_from_pdf(pdf_bytes: bytes) -> Optional[pd.DataFrame]:
    """Extract the main data table from PDF bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    try:
        for page in doc:
            tables = page.find_tables()
            if tables.tables:
                # Get the first (main) table
                df = tables.tables[0].to_pandas()
                return df
    finally:
        doc.close()
    
    return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    try:
        for page in doc:
            text += page.get_text()
    finally:
        doc.close()
    return text


def parse_sitrep_table(df: pd.DataFrame) -> list[dict]:
    """Parse the situation report table into structured district data."""
    districts = []
    
    # The DMC sitrep table has this fixed structure (0-indexed columns):
    # 0: No., 1: Districts, 2: Families affected, 3: People affected, 4: Deaths, 
    # 5: Missing, 6: Houses fully damaged, 7: Houses partially damaged, 
    # 8: Safety centers, 9: Families displaced, 10: People displaced
    cols = list(df.columns)
    
    # Map by position (the structure is consistent across reports)
    col_map = {
        "district": cols[1] if len(cols) > 1 else None,
        "families_affected": cols[2] if len(cols) > 2 else None,
        "people_affected": cols[3] if len(cols) > 3 else None,
        "deaths": cols[4] if len(cols) > 4 else None,
        "missing": cols[5] if len(cols) > 5 else None,
        "houses_fully_damaged": cols[6] if len(cols) > 6 else None,
        "houses_partially_damaged": cols[7] if len(cols) > 7 else None,
        "safety_centers": cols[8] if len(cols) > 8 else None,
        "families_displaced": cols[9] if len(cols) > 9 else None,
        "people_displaced": cols[10] if len(cols) > 10 else None,
    }
    
    # Process each row (skip header rows which are at index 0 and 1)
    for idx, row in df.iterrows():
        # Skip first two rows (headers) and last row (total)
        if idx < 2:
            continue
            
        district_name = row.get(col_map.get("district", ""))
        district_name = normalize_district_name(district_name)
        
        # Skip header rows, empty rows, and total row
        if not district_name or district_name.lower() in ["none", "total", "districts", ""]:
            continue
        
        # Get coordinates for this district
        coords = DISTRICT_COORDS.get(district_name, {"lat": 7.8731, "lon": 80.7718})  # Default to Sri Lanka center
        
        district_data = {
            "district": district_name,
            "lat": coords["lat"],
            "lon": coords["lon"],
            "families_affected": clean_numeric_value(row.get(col_map.get("families_affected", ""), 0)),
            "people_affected": clean_numeric_value(row.get(col_map.get("people_affected", ""), 0)),
            "deaths": clean_numeric_value(row.get(col_map.get("deaths", ""), 0)),
            "missing": clean_numeric_value(row.get(col_map.get("missing", ""), 0)),
            "houses_fully_damaged": clean_numeric_value(row.get(col_map.get("houses_fully_damaged", ""), 0)),
            "houses_partially_damaged": clean_numeric_value(row.get(col_map.get("houses_partially_damaged", ""), 0)),
            "safety_centers": clean_numeric_value(row.get(col_map.get("safety_centers", ""), 0)),
            "families_displaced": clean_numeric_value(row.get(col_map.get("families_displaced", ""), 0)),
            "people_displaced": clean_numeric_value(row.get(col_map.get("people_displaced", ""), 0)),
        }
        
        districts.append(district_data)
    
    return districts


def calculate_totals(districts: list[dict]) -> dict:
    """Calculate aggregate totals from district data."""
    return {
        "total_families_affected": sum(d["families_affected"] for d in districts),
        "total_people_affected": sum(d["people_affected"] for d in districts),
        "total_deaths": sum(d["deaths"] for d in districts),
        "total_missing": sum(d["missing"] for d in districts),
        "total_houses_fully_damaged": sum(d["houses_fully_damaged"] for d in districts),
        "total_houses_partially_damaged": sum(d["houses_partially_damaged"] for d in districts),
        "total_safety_centers": sum(d["safety_centers"] for d in districts),
        "total_families_displaced": sum(d["families_displaced"] for d in districts),
        "total_people_displaced": sum(d["people_displaced"] for d in districts),
        "districts_affected": len(districts),
    }


def extract_sitrep_data(pdf_bytes: bytes) -> dict:
    """
    Main extraction function: Extract all data from a situation report PDF.
    
    Args:
        pdf_bytes: The PDF file content as bytes
        
    Returns:
        Dictionary containing metadata, district data, and totals
    """
    # Extract text for metadata
    text = extract_text_from_pdf(pdf_bytes)
    metadata = extract_metadata_from_text(text)
    
    # Extract table data
    df = extract_table_from_pdf(pdf_bytes)
    if df is None:
        raise ValueError("Could not extract table from PDF")
    
    # Parse district data
    districts = parse_sitrep_table(df)
    
    # Calculate totals
    totals = calculate_totals(districts)
    
    return {
        "metadata": metadata,
        "districts": districts,
        "totals": totals,
    }


def extract_from_file(pdf_path: str | Path) -> dict:
    """
    Extract data from a PDF file path.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing extracted data
    """
    pdf_path = Path(pdf_path)
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    data = extract_sitrep_data(pdf_bytes)
    data["metadata"]["source_file"] = pdf_path.name
    return data


def save_to_json(data: dict, output_path: str | Path) -> None:
    """Save extracted data to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Data saved to {output_path}")


def convert_to_geojson(data: dict) -> dict:
    """Convert extracted data to GeoJSON format for map visualization."""
    features = []
    
    for district in data["districts"]:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [district["lon"], district["lat"]]
            },
            "properties": {
                "district": district["district"],
                "families_affected": district["families_affected"],
                "people_affected": district["people_affected"],
                "deaths": district["deaths"],
                "missing": district["missing"],
                "houses_fully_damaged": district["houses_fully_damaged"],
                "houses_partially_damaged": district["houses_partially_damaged"],
                "safety_centers": district["safety_centers"],
                "families_displaced": district["families_displaced"],
                "people_displaced": district["people_displaced"],
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "metadata": data["metadata"],
        "totals": data["totals"],
        "features": features,
    }


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path> [output_path]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = Path(__file__).parent.parent / "output"
    
    # Extract data
    print(f"Extracting data from: {pdf_path}")
    data = extract_from_file(pdf_path)
    
    # Save as JSON
    json_path = output_dir / "extracted_data.json"
    save_to_json(data, json_path)
    
    # Save as GeoJSON
    geojson_data = convert_to_geojson(data)
    geojson_path = output_dir / "sitrep_data.geojson"
    save_to_json(geojson_data, geojson_path)
    
    # Print summary
    print("\n=== Extraction Summary ===")
    print(f"Report Date: {data['metadata'].get('report_date_formatted', 'Unknown')}")
    print(f"Districts Affected: {data['totals']['districts_affected']}")
    print(f"Total People Affected: {data['totals']['total_people_affected']:,}")
    print(f"Total Families Affected: {data['totals']['total_families_affected']:,}")
    print(f"Total Deaths: {data['totals']['total_deaths']}")
    print(f"Total Missing: {data['totals']['total_missing']}")
    print(f"Total People Displaced: {data['totals']['total_people_displaced']:,}")
