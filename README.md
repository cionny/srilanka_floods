---
title: Sri Lanka Disaster Dashboard
emoji: 🌊
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.28.0
app_file: app.py
pinned: false
license: mit
---

# Sri Lanka Disaster Dashboard 🌊⛰️🇱🇰

Real-time disaster monitoring dashboard using data from the **Disaster Management Centre (DMC)** of Sri Lanka.

## Features

- **📊 Situation Reports**: Flood impact data by district with interactive choropleth maps
- **⛰️ Landslide Warnings**: Active landslide alerts (coming soon)
- **🌊 Flood Warnings**: Active flood alerts (coming soon)

## Data Sources

All data is scraped from the official [DMC Sri Lanka website](https://www.dmc.gov.lk):

**Sit Reps**
- [DMC Situation Reports](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=273&report_type_id=1&lang=en)
- contain infor on deaths, missing, affected, displaced
- scraper should access latest "Situation Report" and scrape content and metadata

**Landslide warnings**
- [Landslide Warning Reports](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en)
- contains a table with the districts and divisions inside the district divided per alert level (level 1 Yellow, level 2 Amber, level 3 Red)
- scraper should access latest "Landslide Early Warning" and scrape the table form page 3 to 5

**River water levels and flood warnings**
- [River Water Level and Flood Warning Reports](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=276&report_type_id=5&lang=en)
- contains info on water level and rainfall in major rivers
- scraper shoudl access latest "water level" and scrape table in page 2

**Weather reports**
- [Weather Rerports](https://www.dmc.gov.lk/index.php?option=com_dmcreports&view=reports&Itemid=274&report_type_id=2&lang=en)
- scraper should access latest "weather forecast" and scrape tables in page 3

There are examples of reports inside `data/reports`

## Tech Stack

- **Streamlit** - Web framework
- **Folium** - Interactive maps
- **PyMuPDF** - PDF extraction
- **BeautifulSoup** - Web scraping
