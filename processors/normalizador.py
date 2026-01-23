# processors/normalizador.py
from datetime import datetime
import hashlib

class NormalizadorMVP:
    """Convierte datos de cualquier origen a formato común"""
    
    def __init__(self):
        # SOLO importar la clase, NO crear instancia
        from models.datos_comunes import EsquemaDatos
        self.EsquemaDatos = EsquemaDatos  # Guardar la clase, no instancia
    
    def normalizar(self, datos_crudos, tipo_fuente, url_original):
        """Transforma datos crudos a formato estándar"""
        
        datos_normalizados = []
        
        if not datos_crudos:
            return datos_normalizados
        
        for i, dato in enumerate(datos_crudos):
            try:
                # Crear ID único
                id_unico = self._generar_id(dato, url_original, i)
                
                # Obtener título
                titulo = dato.get('titulo', '')
                if not titulo:
                    texto = dato.get('texto', dato.get('contenido', ''))
                    titulo = texto[:100] + '...' if len(texto) > 100 else texto
                    if not titulo:
                        titulo = f"Elemento {i+1} de {tipo_fuente}"
                
                # Obtener contenido
                contenido = dato.get('texto', dato.get('contenido', ''))
                if not contenido:
                    contenido = dato.get('descripcion', '')
                
                # Detectar categoría Apple
                categoria = self._detectar_categoria_apple(dato)
                
                # Crear instancia de EsquemaDatos con TODOS los parámetros requeridos
                datos_esquema = {
                    'id_unico': id_unico,
                    'titulo': titulo,
                    'contenido': self._limpiar_texto(contenido),
                    'autor': dato.get('autor', 'Anónimo'),
                    'fecha': self._parsear_fecha(dato.get('fecha', '')),
                    'url': url_original,
                    'tipo_pagina': tipo_fuente,
                    'categoria_producto': categoria,
                    'sentimiento': None,
                    'metadata': {
                        'longitud_texto': len(contenido),
                        'extraido_en': datetime.now().isoformat(),
                        'indice': i
                    }
                }
                
                # Crear instancia validada
                instancia = self.EsquemaDatos(**datos_esquema)
                
                # Convertir a diccionario
                if hasattr(instancia, 'to_dict'):
                    datos_normalizados.append(instancia.to_dict())
                elif hasattr(instancia, 'dict'):
                    datos_normalizados.append(instancia.dict())
                else:
                    datos_normalizados.append(datos_esquema)
                
            except Exception as e:
                print(f"⚠️ Error normalizando dato {i}: {e}")
                # Fallback simple
                datos_normalizados.append({
                    'id_unico': f"error_{i}_{hash(str(dato)) % 1000}",
                    'titulo': dato.get('titulo', 'Error en extracción'),
                    'contenido': str(dato)[:500],
                    'autor': 'Sistema',
                    'fecha': datetime.now().strftime('%Y-%m-%d'),
                    'url': url_original,
                    'tipo_pagina': tipo_fuente,
                    'categoria_producto': 'Error',
                    'sentimiento': None,
                    'metadata': {'error': str(e)}
                })
        
        print(f"✅ Normalizados {len(datos_normalizados)} elementos")
        return datos_normalizados
    
    def _generar_id(self, dato, url, indice):
        """Genera un ID único basado en contenido y URL"""
        contenido = str(dato.get('texto', '')) + url + str(indice)
        return hashlib.md5(contenido.encode()).hexdigest()[:12]
    
    def _limpiar_texto(self, texto):
        """Limpia espacios extras y caracteres extraños"""
        if not texto:
            return ""
        # Limpiar espacios múltiples y saltos de línea
        texto = ' '.join(texto.split())
        # Limitar longitud
        if len(texto) > 5000:
            texto = texto[:5000] + "..."
        return texto
    
    def _parsear_fecha(self, fecha_str):
        """Intenta parsear diferentes formatos de fecha"""
        if not fecha_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        # Simplificado - puedes expandir esto
        fecha_str = str(fecha_str).strip()
        
        # Si ya es una fecha en formato YYYY-MM-DD
        if len(fecha_str) >= 10 and fecha_str[4] == '-' and fecha_str[7] == '-':
            return fecha_str[:10]
        
        return fecha_str  # Devolver como está si no se puede parsear
    
    def _detectar_categoria_apple(self, dato):
        """Detecta de qué producto Apple se habla"""
        texto = ''
        if 'titulo' in dato:
            texto += dato['titulo'].lower() + ' '
        if 'texto' in dato:
            texto += dato['texto'].lower()
        if 'contenido' in dato:
            texto += dato['contenido'].lower()
        
        categorias = {
            'iPhone': ['iphone', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12'],
            'Mac': ['macbook', 'mac', 'imac', 'mac mini', 'mac studio', 'mac pro'],
            'iPad': ['ipad', 'ipad pro', 'ipad air', 'ipad mini'],
            'Watch': ['apple watch', 'watch series', 'watch ultra'],
            'AirPods': ['airpods', 'airpods pro', 'airpods max'],
            'iOS': ['ios', 'ipados', 'macos', 'watchos', 'tvos'],
            'Servicios': ['apple tv+', 'apple music', 'apple arcade', 'icloud', 'app store']
        }
        
        for categoria, keywords in categorias.items():
            for keyword in keywords:
                if keyword.lower() in texto:
                    return categoria
        
        return 'Apple General'
    
    def _determinar_tipo(self, dato, tipo_fuente):
        """Determina si es comentario, post, review, etc."""
        mapeo = {
            'foro': 'comentario_foro',
            'blog': 'comentario_blog',
            'listado': 'item_listado',
            'ecommerce': 'review_producto',
            'noticia': 'articulo',
            'red_social': 'publicacion'
        }
        return mapeo.get(tipo_fuente, 'contenido_generico')