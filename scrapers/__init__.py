# scrapers/__init__.py
"""
Exporta las clases principales de scraping
"""

from .scraper_patrones import ScraperConPatrones
from .scraper_heuristicas import HeuristicasBasicas
from .scraper_hibrido import ScraperHibrido

__all__ = ['ScraperConPatrones', 'HeuristicasBasicas', 'ScraperHibrido']