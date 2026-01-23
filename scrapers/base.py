# scrapers/base.py
from abc import ABC, abstractmethod
import urllib.parse

class BaseScraper(ABC):
    """Clase base abstracta para todos los scrapers"""
    
    def __init__(self, descargador):
        self.descargador = descargador
    
    @abstractmethod
    def puede_manejar(self, url):
        """Debe devolver True si este scraper puede manejar la URL"""
        pass
    
    @abstractmethod
    def scrape(self, url):
        """Método principal de scraping"""
        pass
    
    def extraer_dominio(self, url):
        """Extrae el dominio de una URL"""
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.replace('www.', '')