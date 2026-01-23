# utils/downloader.py - VERSIÓN MEJORADA
import requests
import time
import random
from urllib.parse import urlparse
import json
import os

class DescargadorInteligente:
    """
    Descargador con técnicas anti-bloqueo para sitios de Apple
    """
    
    def __init__(self, delay_min=3, delay_max=7):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.ultimo_request = 0
        
        # Pool de User-Agents realistas
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]
        
        # Headers que parecen de navegador real
        self.headers_base = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        self.session = requests.Session()
        
        # Cache para no repetir descargas
        self.cache_file = 'cache_descargas.json'
        self.cache = self._cargar_cache()
    
    def descargar(self, url, usar_cache=True):
        """
        Descarga inteligente con cache y anti-bloqueo
        """
        # Verificar cache primero
        if usar_cache and url in self.cache:
            print(f"📂 Usando cache para: {self._acortar_url(url)}")
            return self.cache[url]
        
        # Respetar delay aleatorio
        self._delay_aleatorio()
        
        # Headers dinámicos
        headers = self.headers_base.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        
        # Referer aleatorio (opcional, hace parecer tráfico orgánico)
        if random.random() > 0.5:
            headers['Referer'] = 'https://www.google.com/'
        
        try:
            print(f"🌐 Descargando: {self._acortar_url(url)}")
            
            # Request con timeout y verificación SSL
            response = self.session.get(
                url,
                headers=headers,
                timeout=15,
                verify=True,  # IMPORTANTE: True para Apple
                allow_redirects=True
            )
            
            # Manejar códigos de estado
            if response.status_code == 429:  # Too Many Requests
                print(f"⏸️ Rate limit detectado, esperando 30s...")
                time.sleep(30)
                return self.descargar(url, usar_cache=False)
            
            elif response.status_code == 403:  # Forbidden
                print(f"🚫 Acceso denegado (403). Probando con headers diferentes...")
                return self._intentar_con_headers_alternativos(url)
            
            elif response.status_code != 200:
                print(f"⚠️ Código {response.status_code} para {self._acortar_url(url)}")
                return None
            
            # Guardar en cache
            self.cache[url] = response.text
            self._guardar_cache()
            
            self.ultimo_request = time.time()
            return response.text
            
        except requests.exceptions.SSLError:
            print(f"🔒 Error SSL (posible WAF). Intentando sin verificación...")
            return self._descargar_sin_ssl(url)
        
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout. Reintentando...")
            time.sleep(5)
            return self.descargar(url, usar_cache=False)
        
        except Exception as e:
            print(f"❌ Error: {type(e).__name__} - {e}")
            return None
    
    def _delay_aleatorio(self):
        """Delay aleatorio entre requests"""
        tiempo_actual = time.time()
        tiempo_pasado = tiempo_actual - self.ultimo_request
        
        if tiempo_pasado < self.delay_min:
            delay = random.uniform(self.delay_min, self.delay_max)
            espera = delay - tiempo_pasado
            if espera > 0:
                print(f"⏳ Delay aleatorio: {espera:.1f}s")
                time.sleep(espera)
    
    def _intentar_con_headers_alternativos(self, url):
        """Intenta con diferentes headers cuando hay bloqueo"""
        # Headers de navegador móvil
        headers_mobile = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
        }
        
        try:
            response = requests.get(url, headers=headers_mobile, timeout=10)
            if response.status_code == 200:
                print("✅ Desbloqueado con headers móviles")
                return response.text
        except:
            pass
        
        return None
    
    def _descargar_sin_ssl(self, url):
        """Último recurso: sin verificación SSL"""
        try:
            response = requests.get(url, verify=False, timeout=10)
            return response.text if response.status_code == 200 else None
        except:
            return None
    
    def _cargar_cache(self):
        """Carga cache desde archivo"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _guardar_cache(self):
        """Guarda cache en archivo"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def _acortar_url(self, url, max_len=50):
        """Acorta URL para logs"""
        return url if len(url) <= max_len else url[:max_len] + "..."