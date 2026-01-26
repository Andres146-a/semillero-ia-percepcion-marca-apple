# scrapers/scraper_selenium.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

from selenium import webdriver
from selenium.webdriver.edge.options import Options  # ← Cambiado a Edge
from selenium.webdriver.edge.service import Service   # ← Cambiado a Edge
from webdriver_manager.microsoft import EdgeChromiumDriverManager  # ← Driver para Edge

import re

from bs4 import BeautifulSoup
import time
from selenium.common.exceptions import TimeoutException

class ScraperSelenium:
    def __init__(self, headless=True):
        options = Options()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver_path = r"C:\Users\Matias\web-Scraping\drivers\msedgedriver.exe"   
        service = Service(executable_path=driver_path)
        self.driver = webdriver.Edge(service=service, options=options)
        
        self.driver.set_page_load_timeout(30)
    
    def scrape(self, url, max_items=15):
        """
        Scrapea con Selenium y extrae items usando heurísticas simples
        """
        print(f"🌐 Usando Selenium para cargar JS en: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(5)  # Esperar carga inicial
            
            # Scroll lento para cargar más contenido (si infinite scroll)
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            datos = []
            
            # Heurísticas Selenium: buscar contenedores comunes
            contenedores = soup.find_all(['article', 'div', 'li'], class_=True)[:100]
            
            for cont in contenedores:
                item = {}
                
                # Título
                titulo_elem = cont.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if titulo_elem and titulo_elem.get_text(strip=True):
                    item['titulo'] = titulo_elem.get_text(strip=True)[:200]
                
                # Texto/excerpt
                textos = cont.find_all(['p', 'div', 'span'])
                texto_parts = [t.get_text(strip=True) for t in textos if len(t.get_text(strip=True)) > 20]
                if texto_parts:
                    item['contenido'] = ' '.join(texto_parts)[:2000]
                
                # Autor
                autor_elem = cont.find(class_=re.compile(r'author|byline|username', re.I))
                if autor_elem:
                    item['autor'] = autor_elem.get_text(strip=True)
                
                # Fecha
                fecha_elem = cont.find(['time', 'span'], class_=re.compile(r'date|time|posted', re.I))
                if fecha_elem:
                    item['fecha'] = fecha_elem.get_text(strip=True)
                
                if item.get('titulo') or item.get('contenido'):
                    item['url'] = url
                    datos.append(item)
                
                if len(datos) >= max_items:
                    break
            
            print(f"✅ Selenium extrajo {len(datos)} elementos ricos")
            return datos
            
        except TimeoutException:
            print("⏰ Timeout cargando página con Selenium")
            return []
        except Exception as e:
            print(f"❌ Error Selenium: {e}")
            return []
    
    def cerrar(self):
        self.driver.quit()