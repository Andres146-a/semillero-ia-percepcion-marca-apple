# scrapers/scraper_selenium.py
import os
import re
import time
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import TimeoutException


class ScraperSelenium:
    def __init__(self, headless=True, page_load_timeout=30, driver_path=None):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # 1) Prioridad: variable de entorno (evita rutas hardcode)
        env_path = os.getenv("EDGE_DRIVER_PATH")

        # 2) Prioridad: driver_path pasado por parámetro
        candidate = driver_path or env_path

        # 3) Prioridad: driver dentro del repo (drivers/msedgedriver.exe)
        if not candidate:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # raíz del proyecto
            candidate = os.path.join(base_dir, "drivers", "msedgedriver.exe")

        # Si existe local, usarlo
        if os.path.exists(candidate):
            service = Service(candidate)
            self.driver = webdriver.Edge(service=service, options=options)
        else:
            # Si no existe local, intentamos webdriver_manager (requiere internet)
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                service = Service(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=options)
            except Exception as e:
                raise RuntimeError(
                    f"No se encontró msedgedriver local y no se pudo descargar. "
                    f"Coloca el driver en ./drivers/msedgedriver.exe o define EDGE_DRIVER_PATH. "
                    f"Detalle: {e}"
                )

        self.driver.set_page_load_timeout(page_load_timeout)

    def scrape(self, url, max_items=15):
        print(f"🌐 Usando Selenium para cargar JS en: {url}")
        try:
            self.driver.get(url)
            time.sleep(4)

            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            datos = []

            contenedores = soup.find_all(["article", "div", "li"], class_=True)[:150]
            for cont in contenedores:
                item = {}

                titulo_elem = cont.find(["h1", "h2", "h3", "h4", "a"])
                if titulo_elem:
                    t = titulo_elem.get_text(strip=True)
                    if t:
                        item["titulo"] = t[:200]

                textos = cont.find_all(["p", "div", "span"])
                parts = []
                for t in textos:
                    txt = t.get_text(strip=True)
                    if txt and len(txt) > 20:
                        parts.append(txt)
                if parts:
                    item["contenido"] = " ".join(parts)[:2000]

                autor_elem = cont.find(class_=re.compile(r"author|byline|username", re.I))
                if autor_elem:
                    item["autor"] = autor_elem.get_text(strip=True)

                fecha_elem = cont.find(["time", "span"], class_=re.compile(r"date|time|posted", re.I))
                if fecha_elem:
                    item["fecha"] = fecha_elem.get_text(strip=True)

                if item.get("titulo") or item.get("contenido"):
                    item["url"] = url
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
        try:
            self.driver.quit()
        except Exception:
            pass
