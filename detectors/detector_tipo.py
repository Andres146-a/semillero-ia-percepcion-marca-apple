# detectors/detector_tipo.py
import re

class DetectorTipoPagina:
    """Detecta automáticamente el tipo de página web"""
    
    def detectar(self, soup):
        """Analiza el HTML para determinar el tipo de contenido"""
        
        html_str = str(soup)
        texto = soup.get_text().lower()
        
        # Puntuación por tipo
        scores = {
            'foro': 0,
            'blog': 0,
            'listado': 0,
            'ecommerce': 0,
            'red_social': 0
        }
        
        # Análisis de contenido
        scores['foro'] += self._puntuar_foro(soup, texto)
        scores['blog'] += self._puntuar_blog(soup, texto)
        scores['listado'] += self._puntuar_listado(soup)
        
        # Análisis de URL y metadatos
        scores['red_social'] += self._buscar_meta_redes_sociales(soup)
        scores['ecommerce'] += self._buscar_precios_productos(soup)
        
        # Devolver el tipo con mayor puntuación
        tipo_detectado = max(scores, key=scores.get)
        
        # Si la puntuación es muy baja, es "desconocido"
        return tipo_detectado if scores[tipo_detectado] > 2 else 'desconocido'
    
    def _puntuar_foro(self, soup, texto):
        """Busca características de foros"""
        puntuacion = 0
        
        # Palabras clave típicas
        palabras_foro = ['foro', 'tema', 'respuesta', 'post', 'comentario', 'debate']
        for palabra in palabras_foro:
            if palabra in texto:
                puntuacion += 1
        
        # Estructuras HTML típicas
        if soup.find('form', {'id': re.compile(r'post|reply')}):
            puntuacion += 2
        if soup.find('div', {'class': re.compile(r'thread|topic')}):
            puntuacion += 1
        
        return puntuacion