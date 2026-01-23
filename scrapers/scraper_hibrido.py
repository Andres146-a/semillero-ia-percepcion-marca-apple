# scrapers/scraper_hibrido.py
from .scraper_patrones import ScraperConPatrones
from .scraper_heuristicas import HeuristicasBasicas
from detectors.detector_tipo import DetectorTipoPagina
from processors.normalizador import NormalizadorMVP
from .scraper_selenium import ScraperSelenium
import urllib.parse
from .scraper_selenium import ScraperSelenium

class ScraperHibrido:
    """
    ✅ NUEVO: Orquestador que combina patrones + heurísticas
    Decide automáticamente qué estrategia usar
    """
    
    def __init__(self, descargador, normalizador=None):
        self.descargador = descargador
        self.scraper_selenium = None
        self.scraper_patrones = ScraperConPatrones(descargador)
        self.scraper_heuristicas = HeuristicasBasicas(descargador)
        self.detector = DetectorTipoPagina()
        self.normalizador = normalizador or NormalizadorMVP()
    
    def scrape(self, url):
            """
            Flujo principal de scraping híbrido + Selenium fallback
            """
            print(f"\n🔍 Iniciando scraping de: {url}")
            
            datos_normalizados = []
            
            # PASO 1: Intentar con patrones conocidos (más rápido)
            if self.scraper_patrones.puede_manejar(url):
                print("✅ Usando estrategia: PATRÓN CONOCIDO")
                datos_crudos = self.scraper_patrones.scrape(url)
                tipo_fuente = self._obtener_tipo_patron(url)
                
                if datos_crudos:
                    datos_normalizados = self.normalizador.normalizar(datos_crudos, tipo_fuente, url)
                    print(f"   ✅ Patrones extrajeron {len(datos_normalizados)} elementos normalizados")
                    
                    # Si sacó al menos 8 elementos con texto decente → éxito, retornamos
                    if len(datos_normalizados) >= 20 and any(len(d.get('contenido', '')) > 100 for d in datos_normalizados):
                        return datos_normalizados
            
            # PASO 2: Si patrones fallaron o dieron poco → heurísticas con BeautifulSoup
            print("🔄 Usando estrategia: HEURÍSTICAS BS4")
            datos_crudos = self.scraper_heuristicas.scrape(url)
            tipo_fuente = self._inferir_tipo_fuente(url, datos_crudos or [])
            
            if datos_crudos:
                datos_normalizados = self.normalizador.normalizar(datos_crudos, tipo_fuente, url)
                print(f"   ✅ Heurísticas extrajeron {len(datos_normalizados)} elementos normalizados")
                
                # Si sacó buen contenido → éxito
                if len(datos_normalizados) >= 10 and any(len(d.get('contenido', '')) > 80 for d in datos_normalizados):
                    return datos_normalizados
            
            # PASO 3: Fallback final → Selenium (para JS dinámico)
            print("🚀 Activando fallback: SELENIUM (carga JavaScript completo)")
            if self.scraper_selenium is None:
                print("   Inicializando driver de Chrome...")
                self.scraper_selenium = ScraperSelenium(headless=True)
            
            datos_crudos_selenium = self.scraper_selenium.scrape(url, max_items=25)
            
            if datos_crudos_selenium:
                # Usamos tipo genérico o inferido
                tipo_fuente = 'dinamico_js'
                datos_normalizados = self.normalizador.normalizar(datos_crudos_selenium, tipo_fuente, url)
                print(f"   ✅ Selenium extrajo {len(datos_normalizados)} elementos ricos")
                return datos_normalizados
            else:
                print("   ⚠️ Selenium tampoco pudo extraer datos útiles")
            
            # Si todo falló
            print("❌ No se pudieron extraer datos útiles de ningún método")
            return []
    
    def _obtener_tipo_patron(self, url):
        """Obtiene el tipo de fuente desde los patrones configurados"""
        dominio = self.extraer_dominio(url)
        if hasattr(self.scraper_patrones, 'patrones') and dominio in self.scraper_patrones.patrones:
            return self.scraper_patrones.patrones[dominio].get('tipo', 'desconocido')
        return 'patron_conocido'
    
    def _inferir_tipo_fuente(self, url, datos_crudos):
        """Infiere el tipo de fuente cuando no hay patrón"""
        # Preguntar al detector
        dominio = self.extraer_dominio(url)
        
        # Reglas simples basadas en dominio
        if any(palabra in dominio for palabra in ['foro', 'forum', 'board']):
            return 'foro'
        elif any(palabra in dominio for palabra in ['blog', 'medium', 'substack']):
            return 'blog'
        elif any(palabra in dominio for palabra in ['shop', 'store', 'tienda', 'amazon']):
            return 'ecommerce'
        elif any(palabra in dominio for palabra in ['reddit', 'twitter', 'tiktok']):
            return 'red_social'
        
        # Si no se identifica, usar 'desconocido'
        return 'desconocido'
    
    def extraer_dominio(self, url):
        """Extrae el dominio de una URL"""
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.replace('www.', '')    
    
    def cerrar_selenium(self):
        """Cierra el driver de Selenium si está activo"""
        if self.scraper_selenium:
            print("🔻 Cerrando navegador Selenium...")
            self.scraper_selenium.cerrar()
            self.scraper_selenium = None