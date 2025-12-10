"""
PDF Extractor for Sri Lanka DMC Water Level & Rainfall Reports.

Extracts river water level data organized by river basins and tributaries.
The table structure includes:
- River Basin (e.g., "Kelani Ganga (RB 01)")
- Tributory/River (e.g., "Kelani Ganga")
- Gauging Station
- Alert Level, Minor Flood Level, Major Flood Level
- Water Level at two time points
- Remarks (Rising/Falling/Normal)
- 6 Hour Rainfall
"""

import fitz  # PyMuPDF
import re
from datetime import datetime
from typing import Optional
import json


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


def extract_metadata(text: str, pdf_url: str = "") -> dict:
    """
    Extract metadata from the PDF text.
    
    Args:
        text: Full text extracted from PDF
        pdf_url: URL of the PDF file
        
    Returns:
        Dictionary with metadata fields
    """
    metadata = {
        "source": "Disaster Management Center, Sri Lanka",
        "report_type": "Water Level & Rainfall",
        "extracted_at": datetime.now().isoformat(),
        "pdf_url": pdf_url,
    }
    
    # Extract date (format: "7-Dec-2025")
    date_match = re.search(r'DATE\s*:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})', text)
    if date_match:
        date_str = date_match.group(1)
        try:
            report_date = datetime.strptime(date_str, "%d-%b-%Y")
            metadata["report_date"] = report_date.isoformat()
            metadata["report_date_formatted"] = report_date.strftime("%B %d, %Y")
        except ValueError:
            metadata["report_date_str"] = date_str
    
    # Extract time (format: "3:30 PM")
    time_match = re.search(r'TIME\s*:\s*([\d:]+\s*(?:AM|PM|am|pm)?)', text)
    if time_match:
        metadata["report_time"] = time_match.group(1).strip()
    
    # Extract report title
    title_match = re.search(r'(Islandwide Water Level[^\n]+)', text)
    if title_match:
        metadata["report_title"] = title_match.group(1).strip()
    
    return metadata


def parse_water_level_table(text: str) -> list[dict]:
    """
    Parse the water level table from extracted text.
    
    The PDF extraction puts each cell on a separate line.
    Structure for each station row:
    - Tributary name
    - Station name
    - Unit (m or ft)
    - Alert level
    - Minor flood level
    - Major flood level
    - Water level reading 1
    - Water level reading 2
    - Remarks (Normal/Alert/etc or -)
    - Rainfall/trend value
    
    River basins appear as headers with (RB XX) pattern.
    
    Returns:
        List of dictionaries, one per gauging station with river basin info
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    stations = []
    current_basin = "Kelani Ganga (RB 01)"  # Default first basin
    
    # Tributary names to recognize
    tributary_names = [
        'Kelani Ganga', 'Gurugoda Oya', 'Seethawaka Ganga', 'Kehelgamu Oya',
        'Kalu Ganga', 'Maguru Ganga', 'Kuda Ganga', 'Gin Ganga', 
        'Nilwala Ganga', 'Urubokka Ganga', 'Walawe Ganga', 'Kirindi Oya',
        'Kuda Oya', 'Menik Ganga', 'Kumbukkan Oya', 'Heda Oya', 
        'Maduru Oya', 'Mahaweli Ganga', 'Badulu Oya', 'Yan Oya',
        'Mukunu Oya', 'Malwathu Oya', 'Mee Oya', 'Deduru Oya',
        'Maha Oya', 'Attanagalu Oya'
    ]
    
    # Find where data starts (first Kelani Ganga after headers)
    data_start_idx = None
    for i, line in enumerate(lines):
        if line == 'Kelani Ganga' and i > 10:
            data_start_idx = i
            break
    
    if data_start_idx is None:
        return stations
    
    i = data_start_idx
    while i < len(lines):
        line = lines[i]
        
        # Stop at footer
        if 'Prepared by' in line or 'Director' in line or '`' in line:
            break
        
        # Check if this is a river basin header (contains RB XX)
        basin_match = re.search(r'(.+\s+\(RB\s+\d+\))', line)
        if basin_match:
            current_basin = basin_match.group(1).strip()
            i += 1
            continue
        
        # Check if current line is a tributary name
        if line not in tributary_names:
            i += 1
            continue
        
        tributary = line
        i += 1
        
        # Next line should be station name
        if i >= len(lines):
            break
        station = lines[i]
        i += 1
        
        # Next line should be unit
        if i >= len(lines):
            break
        unit = lines[i]
        if unit not in ['m', 'ft']:
            # Not a valid unit, this isn't a data row
            continue
        i += 1
        
        # Next 5 values: alert_level, minor_flood, major_flood, water_level_1, water_level_2
        if i + 4 >= len(lines):
            break
            
        try:
            def parse_float(s):
                """Parse float, return None for NA, -, empty"""
                if not s or s in ['NA', '-']:
                    return None
                try:
                    return float(s)
                except ValueError:
                    return None
            
            alert_level = parse_float(lines[i])
            minor_flood = parse_float(lines[i + 1])
            major_flood = parse_float(lines[i + 2])
            water_level_1 = parse_float(lines[i + 3])
            water_level_2 = parse_float(lines[i + 4])
            i += 5
            
            # Next line: remarks (Normal, Alert, Minor, Major) or - or rainfall value
            remarks = None
            water_level_trend = None
            rainfall_6hr = None
            
            if i < len(lines):
                next_val = lines[i]
                if next_val in ['Normal', 'Alert', 'Minor', 'Major']:
                    remarks = next_val
                    i += 1
                elif next_val != '-':
                    # Try to parse as rainfall
                    rainfall_6hr = parse_float(next_val)
                    if rainfall_6hr is not None:
                        i += 1
                else:
                    i += 1  # Skip '-'
            
            # Next line might be trend (Rising/Falling) or rainfall
            if i < len(lines):
                next_val = lines[i]
                if next_val in ['Rising', 'Falling']:
                    water_level_trend = next_val
                    i += 1
                elif next_val != '-':
                    # Try as rainfall if not already set
                    if rainfall_6hr is None:
                        rainfall_6hr = parse_float(next_val)
                        if rainfall_6hr is not None:
                            i += 1
                else:
                    i += 1  # Skip '-'
            
            station_data = {
                "river_basin": current_basin,
                "tributary": tributary,
                "station": station,
                "unit": unit,
                "alert_level": alert_level,
                "minor_flood_level": minor_flood,
                "major_flood_level": major_flood,
                "water_level_reading_1": water_level_1,
                "water_level_reading_2": water_level_2,
                "remarks": remarks,
                "water_level_trend": water_level_trend,
                "rainfall_6hr_mm": rainfall_6hr,
            }
            
            stations.append(station_data)
            
        except (ValueError, IndexError) as e:
            # Error parsing, skip ahead
            i += 1
            continue
    
    return stations


def extract_flood_data(pdf_bytes: bytes, pdf_url: str = "") -> dict:
    """
    Main extraction function for flood/water level reports.
    
    Args:
        pdf_bytes: PDF file content as bytes
        pdf_url: URL of the PDF file
        
    Returns:
        Dictionary with metadata and stations data
    """
    # Extract text
    text = extract_text_from_pdf(pdf_bytes)
    
    # Extract metadata
    metadata = extract_metadata(text, pdf_url)
    
    # Parse the table
    stations = parse_water_level_table(text)
    
    # Group by river basin
    basins = {}
    for station in stations:
        basin_name = station["river_basin"]
        if basin_name not in basins:
            basins[basin_name] = []
        basins[basin_name].append({
            "tributary": station["tributary"],
            "station": station["station"],
            "unit": station["unit"],
            "alert_level": station["alert_level"],
            "minor_flood_level": station["minor_flood_level"],
            "major_flood_level": station["major_flood_level"],
            "water_level_reading_1": station["water_level_reading_1"],
            "water_level_reading_2": station["water_level_reading_2"],
            "remarks": station["remarks"],
            "water_level_trend": station["water_level_trend"],
            "rainfall_6hr_mm": station["rainfall_6hr_mm"],
        })
    
    # Calculate totals
    totals = {
        "total_stations": len(stations),
        "total_basins": len(basins),
        "stations_with_alert": sum(1 for s in stations if s.get("remarks") == "Alert"),
        "stations_normal": sum(1 for s in stations if s.get("remarks") == "Normal"),
        "stations_rising": sum(1 for s in stations if s.get("water_level_trend") == "Rising"),
        "stations_falling": sum(1 for s in stations if s.get("water_level_trend") == "Falling"),
    }
    
    return {
        "metadata": metadata,
        "river_basins": basins,
        "all_stations": stations,
        "totals": totals,
    }


def scrape_and_save_latest() -> dict:
    """
    Scrape the latest flood report from DMC website and save to data/floods directory.
    
    Returns:
        Extracted data dictionary
    """
    from pathlib import Path
    from . import scraper
    
    print("Fetching latest flood report from DMC website...")
    report_meta = scraper.get_latest_flood_report()
    
    if not report_meta:
        print("No flood report found on website")
        return None
    
    print(f"Found report: {report_meta['title']}")
    print(f"  Date: {report_meta['date']} {report_meta['time']}")
    print(f"  URL: {report_meta['pdf_url']}")
    
    # Download PDF
    print("Downloading PDF...")
    pdf_bytes = scraper.download_pdf(report_meta['pdf_url'])
    print(f"  Downloaded {len(pdf_bytes):,} bytes")
    
    # Extract data
    print("Extracting flood data...")
    data = extract_flood_data(pdf_bytes, report_meta['pdf_url'])
    
    # Generate filename from timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    
    # Extract ID from URL (the numeric part)
    url_id = re.search(r'__(\d+)\.pdf', report_meta['pdf_url'])
    if url_id:
        file_id = url_id.group(1)
        filename = f"flood_data_{file_id}.json"
    else:
        filename = f"flood_data_{timestamp}.json"
    
    # Save to data/floods directory
    data_dir = Path(__file__).parent.parent / "data" / "floods"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = data_dir / filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Also save as latest.json
    latest_file = data_dir / "latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {output_file}")
    print(f"Also saved as: {latest_file}")
    print(f"\nExtraction summary:")
    print(f"  Total stations: {data['totals']['total_stations']}")
    print(f"  Total basins: {data['totals']['total_basins']}")
    print(f"  Stations with alert: {data['totals']['stations_with_alert']}")
    print(f"  Stations normal: {data['totals']['stations_normal']}")
    
    return data


# CLI usage for testing
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scrape":
            # Scrape from website
            data = scrape_and_save_latest()
        else:
            # Extract from local PDF file
            pdf_path = Path(sys.argv[1])
            if pdf_path.exists():
                print(f"Extracting data from {pdf_path}...")
                
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                data = extract_flood_data(pdf_bytes, str(pdf_path))
                
                # Save to output
                output_dir = Path(__file__).parent.parent / "output"
                output_dir.mkdir(exist_ok=True)
                
                output_file = output_dir / "flood_data_test.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"\nExtracted data saved to {output_file}")
                print(f"Total stations: {data['totals']['total_stations']}")
                print(f"Total basins: {data['totals']['total_basins']}")
                print(f"Stations with alert: {data['totals']['stations_with_alert']}")
            else:
                print(f"File not found: {pdf_path}")
    else:
        print("Usage:")
        print("  python flood_extractor.py <pdf_file>  - Extract from local PDF")
        print("  python flood_extractor.py --scrape     - Scrape latest from website")
