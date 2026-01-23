# scrapers/scraper_heuristicas.py
from .base import BaseScraper
from bs4 import BeautifulSoup
import re

class HeuristicasBasicas(BaseScraper):
    """
    Scraper que usa heurísticas para sitios no configurados
    Implementa la clase base abstracta BaseScraper
    """
    
    def __init__(self, descargador):
        super().__init__(descargador)
    
    def puede_manejar(self, url):
        """
        ✅ IMPLEMENTACIÓN DEL MÉTODO ABSTRACTO REQUERIDO
        Este scraper puede manejar cualquier URL
        """
        return True  # Las heurísticas pueden intentar con cualquier sitio
    
    def scrape(self, url):
        """
        ✅ IMPLEMENTACIÓN DEL MÉTODO ABSTRACTO REQUERIDO
        Extrae datos usando heurísticas inteligentes
        """
        print(f"🔍 Usando heurísticas para: {url}")
        
        # Descargar página
        html = self.descargador.descargar(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        datos_extraidos = []
        
        try:
            # Heurística 1: Buscar artículos
            for articulo in soup.find_all(['article', 'div', 'section']):
                item = self._extraer_de_elemento(articulo, url)
                if item:
                    datos_extraidos.append(item)
            
            # Heurística 2: Si no hay artículos, buscar contenedores con clase
            if not datos_extraidos:
                clases_comunes = ['post', 'content', 'main', 'entry', 'blog', 'forum']
                for clase in clases_comunes:
                    for elem in soup.find_all(class_=re.compile(clase, re.I)):
                        item = self._extraer_de_elemento(elem, url)
                        if item:
                            datos_extraidos.append(item)
            
            # Heurística 3: Extraer al menos el título de la página
            if not datos_extraidos:
                titulo = soup.title
                if titulo:
                    datos_extraidos.append({
                        'titulo': titulo.get_text(strip=True),
                        'texto': 'Contenido no extraído por heurísticas',
                        'url_fuente': url,
                        'tipo_fuente': 'desconocido'
                    })
                    
        except Exception as e:
            print(f"❌ Error en heurísticas: {e}")
        
        print(f"📊 Heurísticas extrajeron {len(datos_extraidos)} elementos")
        return datos_extraidos
    
    def _extraer_de_elemento(self, elemento, url):
        """Intenta extraer datos de un elemento HTML"""
        try:
            item = {}
            
            # Buscar título
            titulos = elemento.find_all(['h1', 'h2', 'h3', 'h4'])
            if titulos:
                item['titulo'] = titulos[0].get_text(strip=True)
            
            # Buscar contenido
            parrafos = elemento.find_all('p')
            if parrafos:
                texto = ' '.join([p.get_text(strip=True) for p in parrafos[:3]])
                if texto:
                    item['texto'] = texto
            
            # Buscar autor
            autor_elem = elemento.find(class_=re.compile('author|byline|writer', re.I))
            if autor_elem:
                item['autor'] = autor_elem.get_text(strip=True)
            
            # Buscar fecha
            fecha_elem = elemento.find(class_=re.compile('date|time|posted', re.I))
            if fecha_elem:
                item['fecha'] = fecha_elem.get_text(strip=True)
            
            # Validar que tenga contenido
            if item.get('titulo') or item.get('texto'):
                item['url_fuente'] = url
                item['tipo_fuente'] = self._inferir_tipo(url, elemento)
                return item
            
        except Exception as e:
            print(f"⚠️ Error extrayendo elemento: {e}")
        
        return None
    
    def _inferir_tipo(self, url, elemento):
        """Infiere el tipo de contenido"""
        url_lower = url.lower()
        elemento_str = str(elemento).lower()
        
        if any(word in url_lower for word in ['foro', 'forum', 'board', 'discussion']):
            return 'foro'
        elif any(word in url_lower for word in ['blog', 'article', 'post']):
            return 'blog'
        elif any(word in url_lower for word in ['news', 'noticia', 'report']):
            return 'noticia'
        elif any(word in elemento_str for word in ['comment', 'reply', 'response']):
            return 'comentario'
        
        return 'pagina_web'