"""
Scraper for Sri Lanka DMC Situation Reports.

Fetches situation report PDFs from the Disaster Management Centre website.
"""

import requests
from bs4 import BeautifulSoup
import urllib3
from typing import Optional
import re

# Disable SSL warnings for DMC website (has certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# DMC Website URLs
BASE_URL = "https://www.dmc.gov.lk"

# Correct URL for sitreps (from README)
SITREP_PAGE_URL = (
    "https://www.dmc.gov.lk/index.php?"
    "option=com_dmcreports&view=reports&Itemid=273&report_type_id=1&lang=en"
)

# URL for landslide early warning reports
LANDSLIDE_PAGE_URL = (
    "https://www.dmc.gov.lk/index.php?"
    "option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en"
)

# URL for flood/water level reports
FLOOD_PAGE_URL = (
    "https://www.dmc.gov.lk/index.php?"
    "option=com_dmcreports&view=reports&Itemid=277&report_type_id=6&lang=en"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_sitrep_list(limit: int = 5) -> list[dict]:
    """
    Fetch a list of sitrep metadata from DMC website.
    
    Args:
        limit: Maximum number of reports to return
        
    Returns:
        List of dictionaries with title, date, time, and pdf_url, ordered newest first.
    """
    try:
        response = requests.get(
            SITREP_PAGE_URL, 
            headers=HEADERS, 
            timeout=30, 
            verify=False
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching DMC page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    reports = []
    seen_urls = set()
    
    # Find all PDF links related to situation reports
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True).lower()
        
        # Check if it's a PDF link related to situation reports
        if ".pdf" in href.lower():
            is_sitrep = (
                "situation" in href.lower() or 
                "situation" in text or
                "sitrep" in href.lower() or
                "sitrep" in text
            )
            if is_sitrep:
                # Make URL absolute if relative
                pdf_url = href
                if not pdf_url.startswith("http"):
                    if pdf_url.startswith("/"):
                        pdf_url = f"{BASE_URL}{pdf_url}"
                    else:
                        pdf_url = f"{BASE_URL}/{pdf_url}"
                
                # Skip duplicates
                if pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                
                # Extract metadata
                report_info = _extract_report_metadata(link, pdf_url)
                reports.append(report_info)
    
    # Sort by date (newest first) - reports are usually listed newest first on the page
    # but we'll keep the order as-is since the page already orders them
    
    return reports[:limit]


def _extract_report_metadata(link, pdf_url: str) -> dict:
    """Extract metadata from a report link."""
    # Try to extract metadata from table row
    row = link.find_parent("tr")
    if row:
        cells = row.find_all("td")
        title = cells[0].get_text(strip=True) if cells else ""
        date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        time = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        
        # If first cell is a number (row index), shift
        if cells and cells[0].get_text(strip=True).isdigit():
            title = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            date = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            time = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        
        return {
            "title": title or "Situation Report",
            "date": date,
            "time": time,
            "pdf_url": pdf_url
        }
    else:
        # Extract info from link text or filename
        link_text = link.get_text(strip=True)
        filename = pdf_url.split("/")[-1]
        
        # Try to extract date from filename
        date_match = re.search(r'on[_\s]?(\d{4})', filename)
        time_match = re.search(r'at[_\s]?(\d{4})hrs', filename, re.IGNORECASE)
        
        return {
            "title": link_text or filename.replace("_", " ").replace(".pdf", ""),
            "date": date_match.group(1) if date_match else "",
            "time": f"{time_match.group(1)} hrs" if time_match else "",
            "pdf_url": pdf_url
        }


def get_latest_sitrep() -> dict | None:
    """
    Fetch the latest sitrep metadata from DMC website.
    
    Returns:
        Dictionary with title, date, time, and pdf_url, or None if not found.
    """
    reports = get_sitrep_list(limit=1)
    return reports[0] if reports else None


def get_latest_two_sitreps() -> tuple[dict | None, dict | None]:
    """
    Fetch the two most recent sitreps from DMC website.
    
    Returns:
        Tuple of (latest, previous) report metadata, either can be None.
    """
    reports = get_sitrep_list(limit=2)
    latest = reports[0] if len(reports) > 0 else None
    previous = reports[1] if len(reports) > 1 else None
    return latest, previous


def download_pdf(url: str) -> bytes:
    """
    Download PDF from URL and return bytes.
    
    Args:
        url: URL of the PDF file
        
    Returns:
        PDF file content as bytes
    """
    response = requests.get(url, headers=HEADERS, timeout=60, verify=False)
    response.raise_for_status()
    return response.content


def get_landslide_report_list(limit: int = 5) -> list[dict]:
    """
    Fetch a list of landslide warning report metadata from DMC website.
    
    Args:
        limit: Maximum number of reports to return
        
    Returns:
        List of dictionaries with title, date, time, and pdf_url, ordered newest first.
    """
    try:
        response = requests.get(
            LANDSLIDE_PAGE_URL, 
            headers=HEADERS, 
            timeout=30, 
            verify=False
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching DMC landslide page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    reports = []
    seen_urls = set()
    
    # Find all PDF links related to landslide reports
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True).lower()
        
        # Check if it's a PDF link related to landslide warnings
        if ".pdf" in href.lower():
            is_landslide = (
                "landslide" in href.lower() or 
                "landslide" in text or
                "ew_report" in href.lower() or  # Early Warning Report
                "early warning" in text
            )
            if is_landslide:
                # Make URL absolute if relative
                pdf_url = href
                if not pdf_url.startswith("http"):
                    if pdf_url.startswith("/"):
                        pdf_url = f"{BASE_URL}{pdf_url}"
                    else:
                        pdf_url = f"{BASE_URL}/{pdf_url}"
                
                # Skip duplicates
                if pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                
                # Extract metadata
                report_info = _extract_report_metadata(link, pdf_url)
                report_info["report_type"] = "landslide"
                reports.append(report_info)
    
    return reports[:limit]


def get_latest_landslide_report() -> dict | None:
    """
    Fetch the latest landslide warning report metadata from DMC website.
    
    Returns:
        Dictionary with title, date, time, and pdf_url, or None if not found.
    """
    reports = get_landslide_report_list(limit=1)
    return reports[0] if reports else None


def get_flood_report_list(limit: int = 5) -> list[dict]:
    """
    Fetch a list of flood/water level report metadata from DMC website.
    
    Args:
        limit: Maximum number of reports to return
        
    Returns:
        List of dictionaries with title, date, time, and pdf_url, ordered newest first.
    """
    try:
        response = requests.get(
            FLOOD_PAGE_URL, 
            headers=HEADERS, 
            timeout=30, 
            verify=False
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching DMC flood page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    reports = []
    seen_urls = set()
    
    # Find all PDF links related to water level/rainfall reports
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True).lower()
        
        # Check if it's a PDF link related to water level/flood reports
        if ".pdf" in href.lower():
            is_flood = (
                "water" in href.lower() or 
                "water" in text or
                "rainfall" in href.lower() or
                "rainfall" in text or
                "flood" in href.lower() or
                "flood" in text
            )
            if is_flood:
                # Make URL absolute if relative
                pdf_url = href
                if not pdf_url.startswith("http"):
                    if pdf_url.startswith("/"):
                        pdf_url = f"{BASE_URL}{pdf_url}"
                    else:
                        pdf_url = f"{BASE_URL}/{pdf_url}"
                
                # Skip duplicates
                if pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                
                # Extract metadata
                report_info = _extract_report_metadata(link, pdf_url)
                report_info["report_type"] = "flood"
                reports.append(report_info)
    
    return reports[:limit]


def get_latest_flood_report() -> dict | None:
    """
    Fetch the latest flood/water level report metadata from DMC website.
    
    Returns:
        Dictionary with title, date, time, and pdf_url, or None if not found.
    """
    reports = get_flood_report_list(limit=1)
    return reports[0] if reports else None


# CLI usage for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Testing DMC Scraper")
    print("=" * 60)
    
    print("\nFetching sitrep list...")
    reports = get_sitrep_list(limit=5)
    print(f"Found {len(reports)} situation reports:\n")
    
    for i, report in enumerate(reports):
        print(f"{i+1}. {report['title'][:50]}...")
        print(f"   Date: {report['date']} | Time: {report['time']}")
        print(f"   URL: {report['pdf_url'][:70]}...")
        print()
    
    print("=" * 60)
    print("Testing get_latest_two_sitreps()")
    print("=" * 60)
    
    latest, previous = get_latest_two_sitreps()
    
    if latest:
        print(f"\nLatest report:")
        print(f"  Title: {latest['title']}")
        print(f"  Date: {latest['date']} {latest['time']}")
        
        print("\nDownloading latest PDF...")
        pdf_bytes = download_pdf(latest['pdf_url'])
        print(f"  Downloaded {len(pdf_bytes):,} bytes")
    
    if previous:
        print(f"\nPrevious report:")
        print(f"  Title: {previous['title']}")
        print(f"  Date: {previous['date']} {previous['time']}")
        
        print("\nDownloading previous PDF...")
        pdf_bytes = download_pdf(previous['pdf_url'])
        print(f"  Downloaded {len(pdf_bytes):,} bytes")
    else:
        print("\nNo previous report found")