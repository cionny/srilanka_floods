"""Tab rendering modules for the Sri Lanka Disaster Dashboard."""

from .analytics_tab import render_analytics_tab
from .sitrep_tab import render_sitrep_tab
from .landslide_tab import render_landslide_tab
from .flood_tab import render_flood_tab

__all__ = [
    "render_analytics_tab",
    "render_sitrep_tab",
    "render_landslide_tab",
    "render_flood_tab",
]
