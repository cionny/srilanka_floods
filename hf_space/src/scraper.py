"""
Scraper for Sri Lanka DMC Situation Reports.

Fetches the latest situation report PDF from the Disaster Management Centre website.
"""

import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings for DMC website (has certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# DMC Website URLs
BASE_URL = "https://www.dmc.gov.lk"
SITREP_PAGE_URL = "https://www.dmc.gov.lk/index.php?option=com_content&view=article&id=89&Itemid=308&lang=en"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_latest_sitrep() -> dict | None:
    """
    Fetch the latest sitrep metadata from DMC website.
    
    Returns:
        Dictionary with title, date, time, and pdf_url, or None if not found.
    """
    response = requests.get(SITREP_PAGE_URL, headers=HEADERS, timeout=30, verify=False)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find PDF links in the sitrep table
    pdf_links = soup.find_all("a", href=lambda x: x and "dmcreports" in x.lower() and ".pdf" in x.lower())
    
    if not pdf_links:
        # Try alternative pattern
        pdf_links = soup.find_all("a", href=lambda x: x and ".pdf" in x.lower())
    
    if pdf_links:
        link = pdf_links[0]
        pdf_url = link.get("href")
        
        # Make URL absolute if relative
        if not pdf_url.startswith("http"):
            if pdf_url.startswith("/"):
                pdf_url = f"{BASE_URL}{pdf_url}"
            else:
                pdf_url = f"{BASE_URL}/{pdf_url}"
        
        # Try to extract metadata from table row
        row = link.find_parent("tr")
        if row:
            cells = row.find_all("td")
            return {
                "title": cells[0].get_text(strip=True) if cells else "Situation Report",
                "date": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                "time": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                "pdf_url": pdf_url
            }
        else:
            # Return basic info if no table structure
            return {
                "title": link.get_text(strip=True) or "Situation Report",
                "date": "",
                "time": "",
                "pdf_url": pdf_url
            }
    
    return None


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


# CLI usage for testing
if __name__ == "__main__":
    print("Fetching latest sitrep...")
    sitrep = get_latest_sitrep()
    
    if sitrep:
        print(f"Title: {sitrep['title']}")
        print(f"Date: {sitrep['date']}")
        print(f"Time: {sitrep['time']}")
        print(f"PDF URL: {sitrep['pdf_url']}")
        
        print("\nDownloading PDF...")
        pdf_bytes = download_pdf(sitrep['pdf_url'])
        print(f"Downloaded {len(pdf_bytes)} bytes")
    else:
        print("No sitrep found")