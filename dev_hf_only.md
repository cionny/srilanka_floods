# Sri Lanka Floods - Hugging Face Spaces Only Deployment

## Architecture

```
User → HF Space (Streamlit + Folium)
         ├── Interactive choropleth map
         ├── Refresh button → scrapes DMC, extracts PDF
         ├── Historical data (JSON files in repo)
         └── Diff visualization
```

**Single deployment. No Cloudflare needed.**

---

## Tech Stack

| Component | Tool |
|-----------|------|
| **Frontend** | Streamlit |
| **Map** | Folium (Leaflet wrapper) + streamlit-folium |
| **PDF extraction** | PyMuPDF (existing code) |
| **Scraping** | requests + BeautifulSoup (existing code) |
| **Storage** | JSON files in HF repo (auto-commits) |
| **Hosting** | HF Spaces (Docker) |

---

## Development Plan

### Phase 1: Create Streamlit App

1. Create `app.py` with:
   - Folium choropleth map using `data/districts.geojson`
   - Sidebar with summary stats (deaths, affected, displaced)
   - Refresh button to trigger extraction
   - Historical data selector (dropdown)

2. Reuse existing code:
   - `cloudflare/container/src/extractor.py` → PDF extraction
   - `cloudflare/container/src/scraper.py` → DMC scraping
   - `cloudflare/container/data/districts.geojson` → District polygons

### Phase 2: Data Persistence

1. Store extracted data as `data/sitreps/YYYY-MM-DD.json`
2. On refresh:
   - Extract new data
   - Compare with previous (compute diff)
   - Save to file
   - Use HF `huggingface_hub` to commit changes to repo
3. Alternatively: Use HF Datasets for structured storage

### Phase 3: Deploy to HF Spaces

1. Create Space: `promptaidlabs/srilanka-floods`
2. Upload files:
   ```
      ├── app.py
      ├── requirements.txt
      ├── Dockerfile (or use Streamlit SDK)
      ├── src/
      │   ├── extractor.py
      │   └── scraper.py
      └── data/
         ├── districts.geojson
         └── sitreps/
            └── latest.json
   ```
3. Set Space to public
4. Test at `https://huggingface.co/spaces/promptaidlabs/srilanka-floods`

---

## File Structure

```
├── app.py                 # Main Streamlit app
├── requirements.txt       # streamlit, folium, streamlit-folium, PyMuPDF, etc.
├── Dockerfile             # Optional, can use Streamlit SDK
├── src/
│   ├── __init__.py
│   ├── extractor.py       # Copy from cloudflare/container/src/
│   └── scraper.py         # Copy from cloudflare/container/src/
└── data/
   ├── districts.geojson  # Copy from cloudflare/container/data/
   └── sitreps/
      └── .gitkeep       # Historical data stored here
```
---

## Fallback: VLM Extraction

If PDF table extraction fails, VLM approach available:
- Reference: `arcgis/src/sitrep_ingest.py`
- Add OpenAI Vision call as fallback in `extractor.py`

---

## Quick Start (Local Dev)

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Notes

- HF Spaces with Streamlit SDK auto-restarts on git push
- Free tier: 2 vCPU, 16GB RAM, always-on
- No cold starts (unlike Render free tier)
- URL: `https://promptaidlabs-srilanka-floods.hf.space`
