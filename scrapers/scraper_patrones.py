# scrapers/scraper_patrones.py
import json
import os
import re
from urllib.parse import urlparse
from .base import BaseScraper

class ScraperConPatrones(BaseScraper):
    """
    Scraper que usa patrones pre-configurados para sitios conocidos
    Implementa la clase base abstracta BaseScraper
    """
    
    def __init__(self, descargador):
        super().__init__(descargador)
        self.patrones = self._cargar_patrones()
    
    def puede_manejar(self, url):
        """
        Determina si este scraper puede manejar la URL
        Versión mejorada: busca coincidencias parciales
        """
        dominio = self.extraer_dominio(url)
        
        # 1. Buscar coincidencia exacta de dominio
        if dominio in self.patrones:
            return True
        
        # 2. Buscar coincidencia parcial en las claves
        for key in self.patrones.keys():
            if dominio in key or key in url:
                return True
        
        # 3. Para sitios Apple específicos
        if 'apple' in dominio:
            # Buscar cualquier patrón que sea para Apple
            for key, patron in self.patrones.items():
                if patron.get('marca') == 'Apple' and dominio in patron.get('url', ''):
                    return True
        
        return False
    
    def scrape(self, url):
        """
        Extrae datos usando patrones pre-configurados
        Versión mejorada con lógica de fallback
        """
        if not self.puede_manejar(url):
            print(f"⚠️ No hay patrón para: {url}")
            return []
        
        dominio = self.extraer_dominio(url)
        
        # Encontrar el patrón correcto (puede haber coincidencia parcial)
        patron = None
        if dominio in self.patrones:
            patron = self.patrones[dominio]
        else:
            # Buscar coincidencia parcial
            for key, value in self.patrones.items():
                if dominio in key or key in url:
                    patron = value
                    print(f"🔍 Coincidencia parcial: {key} → {dominio}")
                    break
        
        if not patron:
            print(f"⚠️ No se encontró patrón para: {dominio}")
            return []
        
        print(f"✅ Usando patrón para: {dominio} ({patron.get('tipo', 'desconocido')})")
        
        # Descargar página
        html = self.descargador.descargar(url)
        if not html:
            return []
        
        # Parsear con BeautifulSoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        datos_extraidos = []
        
        try:
            # Primero intentar con patrones específicos
            datos_extraidos = self._extraer_con_patrones(soup, patron, url)
            
            # Si no funciona, intentar con heurísticas de respaldo
            if len(datos_extraidos) == 0:
                print("⚠️ Patrones no funcionaron, intentando heurísticas de respaldo...")
                datos_extraidos = self._extraer_con_fallback(soup, url, patron)
            
        except Exception as e:
            print(f"❌ Error en scraping por patrones: {e}")
            # Último recurso: intentar fallback
            datos_extraidos = self._extraer_con_fallback(soup, url, patron)
        
        print(f"📊 Extraídos {len(datos_extraidos)} elementos de {dominio}")
        return datos_extraidos
    # En scraper_patrones.py, añade este método para extracción profunda
    def _extraer_texto_completo(self, contenedor, selectores, url):
        """Estrategia exhaustiva para extraer el máximo texto posible"""
        texto_completo = []
        
        # 1. Intentar con el selector específico del patrón
        if 'texto' in selectores:
            elementos = contenedor.select(selectores['texto'])
            for elem in elementos[:5]:  # Limitar a 5 elementos
                texto = elem.get_text(' ', strip=True)
                if len(texto) > 50:  # Solo texto significativo
                    texto_completo.append(texto)
        
        # 2. Si no hay suficiente texto, buscar todos los párrafos
        if len(' '.join(texto_completo)) < 200:
            parrafos = contenedor.find_all('p')
            for p in parrafos[:10]:
                texto = p.get_text(' ', strip=True)
                if len(texto) > 30:
                    texto_completo.append(texto)
        
        # 3. Último recurso: extraer todo el texto del contenedor
        if len(' '.join(texto_completo)) < 100:
            todo_texto = contenedor.get_text(' ', strip=True)
            # Limpiar texto excesivamente largo
            lines = todo_texto.split('. ')
            texto_completo.extend([line for line in lines[:15] if len(line) > 20])
        
        return ' '.join(texto_completo)[:3000]  # Limitar a 3000 caracteres
    def _extraer_texto_completo(self, contenedor, selectores, url):
        """Estrategia exhaustiva para extraer el máximo texto posible"""
        texto_completo = []
        
        print(f"    Usando extracción completa...")
        
        # 1. Intentar con CADA selector de texto (no solo el primero)
        if 'texto' in selectores:
            for selector in selectores['texto'].split(', '):
                elementos = contenedor.select(selector.strip())
                for elem in elementos[:3]:
                    texto = elem.get_text(' ', strip=True)
                    if len(texto) > 30:
                        texto_completo.append(texto)
                        print(f"      Selector '{selector}': {len(texto)} chars")
        
        # 2. Si no hay suficiente texto, buscar todos los párrafos
        if len(' '.join(texto_completo)) < 100:
            parrafos = contenedor.find_all('p')
            print(f"      Encontrados {len(parrafos)} párrafos")
            for p in parrafos[:15]:
                texto = p.get_text(' ', strip=True)
                if len(texto) > 20:
                    texto_completo.append(texto)
        
        # 3. Último recurso: extraer todo el texto del contenedor
        if len(' '.join(texto_completo)) < 50:
            todo_texto = contenedor.get_text(' ', strip=True)
            # Dividir en oraciones significativas
            oraciones = [o.strip() for o in todo_texto.split('. ') if 20 < len(o.strip()) < 300]
            texto_completo.extend(oraciones[:10])
            print(f"      Extraído texto crudo: {len(todo_texto)} chars total")
        
        resultado = ' '.join(texto_completo)
        
        if resultado:
            resultado = ' '.join(resultado.split())[:3000]
            print(f"      Resultado final: {len(resultado)} caracteres")
        
        return resultado

    def _extraer_con_patrones(self, soup, patron, url):
        """Extracción usando los selectores del patrón"""
        datos = []
        selectores = patron.get('selectores', {})
        
        print(f"🔍 PATRÓN ACTIVO: {json.dumps(selectores, indent=2)}") 
        
        # Buscar contenedores principales
        selector_contenedor = selectores.get('contenedor', 'body')
        contenedores = soup.select(selector_contenedor)
        
        print(f"🔍 Encontrados {len(contenedores)} contenedores con selector: {selector_contenedor}")
        
        for i, contenedor in enumerate(contenedores[:3]):  # Solo primeros 3 para diagnóstico
            try:
                item = {}
                
                # DIAGNÓSTICO: Mostrar qué estamos viendo
                print(f"\n🔍 ANALIZANDO CONTENEDOR {i}:")
                print(f"  HTML: {str(contenedor)[:200]}...")
                
                # Prueba cada selector
                for clave, selector in selectores.items():
                    elementos = contenedor.select(selector)
                    print(f"  Selector '{clave}' ('{selector}'): {len(elementos)} elementos encontrados")
                    
                    if elementos and clave in ['texto', 'contenido']:
                        print(f"    Texto del primer elemento: {elementos[0].get_text(strip=True)[:100]}...")
                
                # Extraer título
                if 'titulo' in selectores:
                    titulo_elem = contenedor.select_one(selectores['titulo'])
                    if titulo_elem:
                        item['titulo'] = titulo_elem.get_text(strip=True)
                
                # Extraer contenido/texto con estrategia mejorada
                item['texto'] = self._extraer_texto_mejorado(contenedor, selectores)
                
                # Si aún no hay texto, usar método exhaustivo
                if not item.get('texto') or len(item['texto'].strip()) < 20:
                    item['texto'] = self._extraer_texto_completo(contenedor, selectores, url)
                
                # Extraer autor
                if 'autor' in selectores:
                    autor_elem = contenedor.select_one(selectores['autor'])
                    if autor_elem:
                        item['autor'] = autor_elem.get_text(strip=True)
                
                # Extraer fecha
                if 'fecha' in selectores:
                    fecha_elem = contenedor.select_one(selectores['fecha'])
                    if fecha_elem:
                        item['fecha'] = fecha_elem.get_text(strip=True)
                
                # Si se extrajo algún dato, agregarlo
                if item.get('titulo') or item.get('texto'):
                    item['url_fuente'] = url
                    item['tipo_fuente'] = patron.get('tipo', 'desconocido')
                    datos.append(item)
                    print(f"✅ Elemento {i} extraído: '{item.get('titulo', 'Sin título')[:50]}...'")
                    
            except Exception as e:
                print(f"⚠️ Error en elemento {i}: {e}")
                continue
        
        return datos


    def _extraer_texto_mejorado(self, contenedor, selectores):
        """Extrae texto usando TODOS los selectores posibles"""
        textos = []
        
        # 1. Usar selectores de texto del patrón (TODOS los elementos)
        if 'texto' in selectores:
            elementos = contenedor.select(selectores['texto'])
            for elem in elementos[:3]:  # Primeros 3 elementos
                texto = elem.get_text(' ', strip=True)
                if texto and len(texto) > 10:
                    textos.append(texto)
        
        # 2. Si no hay suficiente, usar selector de contenido
        if len(' '.join(textos)) < 50 and 'contenido' in selectores:
            elementos = contenedor.select(selectores['contenido'])
            for elem in elementos[:2]:
                texto = elem.get_text(' ', strip=True)
                if texto and len(texto) > 10:
                    textos.append(texto)
        
        # 3. Si aún no hay, buscar párrafos
        if len(' '.join(textos)) < 100:
            parrafos = contenedor.find_all('p')
            for p in parrafos[:5]:
                texto = p.get_text(' ', strip=True)
                if texto and len(texto) > 20:
                    textos.append(texto)
        
        # 4. Extraer de spans y divs con texto
        if len(' '.join(textos)) < 100:
            elementos_texto = contenedor.find_all(['span', 'div'], string=True)
            for elem in elementos_texto[:10]:
                texto = elem.get_text(' ', strip=True)
                if texto and 20 < len(texto) < 500:
                    textos.append(texto)
        
        resultado = ' '.join(textos)
        
        # Limpiar resultado
        if resultado:
            # Eliminar espacios múltiples
            resultado = ' '.join(resultado.split())
            # Limitar longitud
            if len(resultado) > 3000:
                resultado = resultado[:3000] + "..."
        
        print(f"    Texto extraído mejorado: {len(resultado)} caracteres")
        return resultado
        
    
    
    
    
    
    
    
    
    
    
    
    
    def _extraer_con_fallback(self, soup, url, patron):
        """Extracción de respaldo cuando los selectores específicos fallan"""
        datos = []
        
        print("🔄 Usando estrategia de fallback...")
        
        # Strategy 1: Buscar cualquier article o contenedor semántico
        contenedores = soup.find_all(['article', 'section', 'div'], class_=True)
        
        if not contenedores:
            # Strategy 2: Buscar cualquier elemento con clase que contenga post/article/thread
            contenedores = soup.find_all(class_=re.compile(r'(post|article|thread|discussion|message|item)', re.I))
        
        if not contenedores:
            # Strategy 3: Buscar cualquier div con clase
            contenedores = soup.find_all('div', class_=True)[:50]  # Limitar a 50
        
        print(f"🔍 Fallback: {len(contenedores)} elementos potenciales")
        
        for i, contenedor in enumerate(contenedores[:30]):  # Limitar a 30
            try:
                item = {}
                
                # Buscar título (cualquier h1-h3)
                titulo_elem = contenedor.find(['h1', 'h2', 'h3', 'h4'])
                if titulo_elem:
                    item['titulo'] = titulo_elem.get_text(strip=True)
                
                # Si no hay título específico, buscar en textos grandes
                if not item.get('titulo'):
                    textos_grandes = contenedor.find_all(['p', 'span', 'div'], string=True)
                    if textos_grandes:
                        # Tomar el texto más largo como posible título
                        textos = [t.get_text(strip=True) for t in textos_grandes if len(t.get_text(strip=True)) > 20]
                        if textos:
                            item['titulo'] = textos[0][:100]
                
                # Buscar texto (párrafos)
                parrafos = contenedor.find_all('p')
                if parrafos:
                    texto = ' '.join([p.get_text(strip=True) for p in parrafos[:5]])
                    if texto and len(texto) > 10:  # Solo si tiene suficiente contenido
                        item['texto'] = texto[:1000]  # Limitar
                
                # Buscar autor
                autor_elem = contenedor.find(class_=re.compile(r'(author|byline|user|username|writer)', re.I))
                if autor_elem:
                    item['autor'] = autor_elem.get_text(strip=True)
                
                # Buscar fecha
                fecha_elem = contenedor.find(class_=re.compile(r'(date|time|posted|datetime|published)', re.I))
                if not fecha_elem:
                    fecha_elem = contenedor.find('time')
                if fecha_elem:
                    item['fecha'] = fecha_elem.get_text(strip=True)
                
                # Solo agregar si tiene contenido útil
                if item.get('titulo') or item.get('texto'):
                    item['url_fuente'] = url
                    item['tipo_fuente'] = patron.get('tipo', 'desconocido')
                    
                    # Detectar si es Apple relacionado
                    contenido_completo = (item.get('titulo', '') + ' ' + item.get('texto', '')).lower()
                    if any(keyword in contenido_completo for keyword in ['iphone', 'ipad', 'mac', 'apple', 'ios', 'watch']):
                        datos.append(item)
                    elif patron.get('marca') == 'Apple':  # Si el patrón es de Apple, asumir que es relevante
                        datos.append(item)
                        
            except Exception as e:
                continue
        
        print(f"📊 Fallback extrajo {len(datos)} elementos válidos")
        return datos
    
    def extraer_dominio(self, url):
        """Extrae el dominio de una URL"""
        parsed = urlparse(url)
        dominio = parsed.netloc.replace('www.', '').lower()
        return dominio
    
    def _cargar_patrones(self):
        """Carga los patrones desde el archivo JSON"""
        try:
            ruta_patrones = os.path.join('config', 'patrones.json')
            if os.path.exists(ruta_patrones):
                with open(ruta_patrones, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️ Archivo {ruta_patrones} no encontrado")
                return {}
        except Exception as e:
            print(f"⚠️ Error cargando patrones: {e}")
            return {}