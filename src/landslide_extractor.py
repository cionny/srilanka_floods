"""
PDF Extractor for Sri Lanka DMC Landslide Early Warning Reports.

Extracts division-level landslide warnings by alert level (Yellow, Amber, Red).
The table structure is:
- Column 1: District name
- Column 2: Level 1 (Yellow) - comma-separated division names
- Column 3: Level 2 (Amber) - comma-separated division names
- Column 4: Level 3 (Red) - comma-separated division names
"""

import fitz  # PyMuPDF
import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


# Alert level configuration for map visualization
ALERT_LEVELS = {
    0: {"name": "No Warning", "color": "#f7f7f7", "risk": "None"},
    1: {"name": "Yellow", "color": "#FFFF00", "risk": "Low"},
    2: {"name": "Amber", "color": "#FFA500", "risk": "Medium"},
    3: {"name": "Red", "color": "#FF0000", "risk": "High"},
}


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


def extract_landslide_tables(pdf_bytes: bytes) -> list[pd.DataFrame]:
    """
    Extract landslide warning tables from the PDF.
    
    The main table typically starts on page 3 and may span multiple pages.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    tables = []
    
    try:
        # Try pages 2-6 (0-indexed), as the table can span multiple pages
        for page_num in range(2, min(7, len(doc))):
            page = doc[page_num]
            page_tables = page.find_tables()
            
            for table in page_tables.tables:
                df = table.to_pandas()
                # Only include tables that look like the warning table
                # (have at least 2 columns and some rows)
                if df is not None and len(df.columns) >= 2 and len(df) > 0:
                    tables.append(df)
    finally:
        doc.close()
    
    return tables


def parse_divisions(cell_value) -> list[str]:
    """
    Parse comma-separated division names from a cell.
    
    Handles:
    - Multiple divisions: "Ella, Badulla, Hali-Ela"
    - Single division: "Ella"
    - Empty: "-", "", None
    - Multi-line text with extra PDF annotations
    """
    if cell_value is None or pd.isna(cell_value):
        return []
    
    cell_str = str(cell_value).strip()
    
    # Skip empty indicators
    if cell_str in ["-", "", "None", "nan"]:
        return []
    
    # Clean up common PDF extraction artifacts
    # Remove common footer text that gets mixed in
    artifacts_to_remove = [
        "Divisional Secretariat",
        "Division(s) (DSD)",
        "DSD",
        "and surrounding areas",
        "surrounding areas",
        "(DSD)",
    ]
    for artifact in artifacts_to_remove:
        cell_str = cell_str.replace(artifact, "")
    
    # Replace newlines and multiple spaces with single space
    cell_str = re.sub(r'\s+', ' ', cell_str)
    
    # Remove arrows/special characters that may appear
    cell_str = cell_str.replace("↓", "").replace("↑", "").replace("_", "")
    
    # Split by comma and "and" (as "and" is sometimes used instead of comma)
    # First replace " and " with comma to normalize
    cell_str = re.sub(r'\s+and\s+', ', ', cell_str, flags=re.IGNORECASE)
    
    # Split by comma and clean up each division name
    divisions = []
    for part in cell_str.split(","):
        division = part.strip()
        
        # Filter out empty strings and short/invalid values
        if not division or len(division) < 3:
            continue
        if division.lower() in ["-", "none", "nan", "."]:
            continue
        # Skip if it looks like a number only
        if division.isdigit():
            continue
            
        divisions.append(division)
    
    return divisions


def normalize_district_name(name: str) -> str:
    """Normalize district name for consistency with sitrep data."""
    if name is None or pd.isna(name):
        return ""
    
    name = str(name).strip()
    
    # Handle alternative spellings
    name_mapping = {
        "Rathnapura": "Ratnapura",
        "NuwaraEliya": "Nuwara Eliya",
        "Nuwaraeliya": "Nuwara Eliya",
    }
    
    return name_mapping.get(name, name)


def parse_landslide_table(df: pd.DataFrame) -> list[dict]:
    """
    Parse the landslide warning table into structured district data.
    
    Expected structure:
    - Column 0 or 1: District name (may have a row number in column 0)
    - Following columns: Level 1, Level 2, Level 3 warnings
    """
    warnings = []
    
    cols = list(df.columns)
    if len(cols) < 2:
        return warnings
    
    # Detect column structure
    # Sometimes first column is row number, sometimes it's district name
    district_col = None
    level_cols = {"level_1": None, "level_2": None, "level_3": None}
    
    # Try to identify columns by header content
    for idx, col in enumerate(cols):
        col_str = str(col).lower()
        
        if "district" in col_str:
            district_col = col
        elif "level 1" in col_str or "yellow" in col_str:
            level_cols["level_1"] = col
        elif "level 2" in col_str or "amber" in col_str:
            level_cols["level_2"] = col
        elif "level 3" in col_str or "red" in col_str:
            level_cols["level_3"] = col
    
    # Fallback: assume positional structure if headers not detected
    if district_col is None:
        # Check if first column looks like row numbers
        first_col_values = df[cols[0]].dropna().astype(str).tolist()[:5]
        has_numbers = all(v.isdigit() or v.lower() in ["no", "no."] for v in first_col_values if v)
        
        if has_numbers and len(cols) >= 5:
            # First col is row number, second is district
            district_col = cols[1]
            level_cols = {
                "level_1": cols[2] if len(cols) > 2 else None,
                "level_2": cols[3] if len(cols) > 3 else None,
                "level_3": cols[4] if len(cols) > 4 else None,
            }
        elif len(cols) >= 4:
            # First col is district
            district_col = cols[0]
            level_cols = {
                "level_1": cols[1] if len(cols) > 1 else None,
                "level_2": cols[2] if len(cols) > 2 else None,
                "level_3": cols[3] if len(cols) > 3 else None,
            }
    
    if district_col is None:
        return warnings
    
    # Process each row
    for idx, row in df.iterrows():
        district_name = str(row.get(district_col, "")).strip()
        district_name = normalize_district_name(district_name)
        
        # Skip header rows, empty rows, and total rows
        skip_values = [
            "", "none", "district", "districts", "total", "grand total",
            "no", "no.", "sl no", "sl.no", "0", "1", "2", "3", "4", "5",
            "level 1", "level 2", "level 3", "yellow", "amber", "red"
        ]
        if not district_name or district_name.lower() in skip_values:
            continue
        
        # Skip if district name is a number (row index)
        if district_name.isdigit():
            continue
        
        # Parse divisions for each level
        level_1_divs = parse_divisions(row.get(level_cols["level_1"], "")) if level_cols["level_1"] else []
        level_2_divs = parse_divisions(row.get(level_cols["level_2"], "")) if level_cols["level_2"] else []
        level_3_divs = parse_divisions(row.get(level_cols["level_3"], "")) if level_cols["level_3"] else []
        
        # Calculate max alert level for this district
        if len(level_3_divs) > 0:
            max_level = 3
        elif len(level_2_divs) > 0:
            max_level = 2
        elif len(level_1_divs) > 0:
            max_level = 1
        else:
            max_level = 0
        
        district_data = {
            "district": district_name,
            "level_1_divisions": level_1_divs,
            "level_2_divisions": level_2_divs,
            "level_3_divisions": level_3_divs,
            "level_1_count": len(level_1_divs),
            "level_2_count": len(level_2_divs),
            "level_3_count": len(level_3_divs),
            "total_warnings": len(level_1_divs) + len(level_2_divs) + len(level_3_divs),
            "max_level": max_level,
        }
        
        warnings.append(district_data)
    
    return warnings


def extract_metadata_from_text(text: str) -> dict:
    """Extract report metadata from PDF text."""
    metadata = {
        "source": "Disaster Management Center, Sri Lanka",
        "report_type": "Landslide Early Warning",
        "extracted_at": datetime.now().isoformat(),
    }
    
    # Pattern 1: "at 1600hrs on 2025.01.15"
    pattern1 = r"at\s*(\d{4})\s*hrs?\s*on\s*(\d{4}[.\-/]\d{2}[.\-/]\d{2})"
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        time_str = match.group(1)
        date_str = match.group(2).replace("/", ".").replace("-", ".")
        try:
            report_date = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H%M")
            metadata["report_date"] = report_date.isoformat()
            metadata["report_date_formatted"] = report_date.strftime("%B %d, %Y at %H:%M hrs")
        except ValueError:
            metadata["report_date_raw"] = f"{date_str} {time_str}"
    else:
        # Pattern 2: Try to extract from filename or other patterns
        # "Landslide EW Report at 1600hrs on 2025"
        pattern2 = r"(\d{4})[.\-/](\d{2})[.\-/](\d{2})"
        match2 = re.search(pattern2, text[:500])  # Look in first 500 chars
        if match2:
            try:
                report_date = datetime.strptime(
                    f"{match2.group(1)}.{match2.group(2)}.{match2.group(3)}", 
                    "%Y.%m.%d"
                )
                metadata["report_date"] = report_date.isoformat()
                metadata["report_date_formatted"] = report_date.strftime("%B %d, %Y")
            except ValueError:
                metadata["report_date_raw"] = "Unknown"
        else:
            metadata["report_date_raw"] = "Unknown"
    
    return metadata


def calculate_totals(districts: list[dict]) -> dict:
    """Calculate aggregate totals from district data."""
    return {
        "districts_with_warnings": len([d for d in districts if d["total_warnings"] > 0]),
        "districts_level_3": len([d for d in districts if d["level_3_count"] > 0]),
        "districts_level_2": len([d for d in districts if d["level_2_count"] > 0]),
        "districts_level_1": len([d for d in districts if d["level_1_count"] > 0]),
        "total_level_1": sum(d["level_1_count"] for d in districts),
        "total_level_2": sum(d["level_2_count"] for d in districts),
        "total_level_3": sum(d["level_3_count"] for d in districts),
        "total_divisions_affected": sum(d["total_warnings"] for d in districts),
    }


def merge_district_warnings(warnings_list: list[dict]) -> list[dict]:
    """
    Merge warnings for the same district (in case table spans pages).
    
    Deduplicates by district name and combines division lists.
    """
    district_map = {}
    
    for w in warnings_list:
        district = w["district"]
        
        if district in district_map:
            # Merge divisions (avoid duplicates)
            existing = district_map[district]
            for level in ["level_1", "level_2", "level_3"]:
                key = f"{level}_divisions"
                existing_divs = set(existing[key])
                new_divs = set(w[key])
                existing[key] = list(existing_divs | new_divs)
                existing[f"{level}_count"] = len(existing[key])
            
            # Recalculate totals
            existing["total_warnings"] = (
                existing["level_1_count"] + 
                existing["level_2_count"] + 
                existing["level_3_count"]
            )
            
            # Recalculate max level
            if existing["level_3_count"] > 0:
                existing["max_level"] = 3
            elif existing["level_2_count"] > 0:
                existing["max_level"] = 2
            elif existing["level_1_count"] > 0:
                existing["max_level"] = 1
            else:
                existing["max_level"] = 0
        else:
            district_map[district] = w.copy()
    
    return list(district_map.values())


def extract_landslide_data(pdf_bytes: bytes) -> dict:
    """
    Main extraction function: Extract all data from a landslide warning PDF.
    
    Args:
        pdf_bytes: The PDF file content as bytes
        
    Returns:
        Dictionary containing metadata, district warnings, and totals
    """
    # Extract text for metadata
    text = extract_text_from_pdf(pdf_bytes)
    metadata = extract_metadata_from_text(text)
    
    # Extract and parse tables
    tables = extract_landslide_tables(pdf_bytes)
    
    all_warnings = []
    for df in tables:
        warnings = parse_landslide_table(df)
        all_warnings.extend(warnings)
    
    # Merge duplicate districts (from multi-page tables)
    districts = merge_district_warnings(all_warnings)
    
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
    
    data = extract_landslide_data(pdf_bytes)
    data["metadata"]["source_file"] = pdf_path.name
    return data


def convert_to_geojson(data: dict, districts_geojson: dict) -> dict:
    """
    Merge landslide warning data with district GeoJSON boundaries.
    
    Creates a GeoJSON with district polygons colored by max alert level.
    
    Args:
        data: Extracted landslide data
        districts_geojson: District boundaries GeoJSON
        
    Returns:
        GeoJSON FeatureCollection with landslide data in properties
    """
    import copy
    
    # Create a lookup for landslide data by district
    landslide_lookup = {d["district"]: d for d in data.get("districts", [])}
    
    # Deep copy to avoid modifying original
    geojson = copy.deepcopy(districts_geojson)
    
    # Add landslide data to each district feature
    for feature in geojson["features"]:
        district_name = feature["properties"].get("district", "")
        
        if district_name in landslide_lookup:
            warning = landslide_lookup[district_name]
            feature["properties"].update({
                "max_level": warning["max_level"],
                "level_1_count": warning["level_1_count"],
                "level_2_count": warning["level_2_count"],
                "level_3_count": warning["level_3_count"],
                "total_warnings": warning["total_warnings"],
                "level_1_divisions": warning["level_1_divisions"],
                "level_2_divisions": warning["level_2_divisions"],
                "level_3_divisions": warning["level_3_divisions"],
            })
        else:
            # No warnings for this district
            feature["properties"].update({
                "max_level": 0,
                "level_1_count": 0,
                "level_2_count": 0,
                "level_3_count": 0,
                "total_warnings": 0,
                "level_1_divisions": [],
                "level_2_divisions": [],
                "level_3_divisions": [],
            })
    
    # Add metadata and totals
    geojson["metadata"] = data.get("metadata", {})
    geojson["totals"] = data.get("totals", {})
    
    return geojson


# CLI usage
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python landslide_extractor.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print(f"Extracting landslide data from: {pdf_path}")
    data = extract_from_file(pdf_path)
    
    # Print summary
    print("\n=== Extraction Summary ===")
    print(f"Report Date: {data['metadata'].get('report_date_formatted', data['metadata'].get('report_date_raw', 'Unknown'))}")
    print(f"Districts with Warnings: {data['totals']['districts_with_warnings']}")
    print(f"  - Level 3 (Red): {data['totals']['districts_level_3']} districts, {data['totals']['total_level_3']} divisions")
    print(f"  - Level 2 (Amber): {data['totals']['districts_level_2']} districts, {data['totals']['total_level_2']} divisions")
    print(f"  - Level 1 (Yellow): {data['totals']['districts_level_1']} districts, {data['totals']['total_level_1']} divisions")
    print(f"Total Divisions Affected: {data['totals']['total_divisions_affected']}")
    
    print("\n=== District Details ===")
    for d in sorted(data["districts"], key=lambda x: x["max_level"], reverse=True):
        if d["total_warnings"] > 0:
            level_str = ["None", "Yellow", "Amber", "Red"][d["max_level"]]
            print(f"\n{d['district']} (Max: {level_str}):")
            if d["level_3_divisions"]:
                print(f"  🔴 Red: {', '.join(d['level_3_divisions'])}")
            if d["level_2_divisions"]:
                print(f"  🟠 Amber: {', '.join(d['level_2_divisions'])}")
            if d["level_1_divisions"]:
                print(f"  🟡 Yellow: {', '.join(d['level_1_divisions'])}")
    
    # Optionally save to JSON
    output_path = Path(pdf_path).with_suffix(".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nData saved to: {output_path}")
