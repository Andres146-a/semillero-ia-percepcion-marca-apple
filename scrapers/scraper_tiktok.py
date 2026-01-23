# scrapers/scraper_tiktok.py
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime

class ScraperTikTok:
    def __init__(self, headless=True):
        options = Options()
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Anti-detection mejorada
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Driver path manual
        driver_path = r"C:\Users\Matias\web-Scraping\drivers\msedgedriver.exe"
        service = Service(executable_path=driver_path)

        self.driver = webdriver.Edge(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
        print("✅ Driver Edge inicializado con anti-detection optimizada para TikTok")

    def scrape_comments_keywords(self, keywords, max_videos=5, max_comments_per_video=30):
        todos_comentarios = []
        keyword_list = [keywords] if isinstance(keywords, str) else keywords

        for keyword in keyword_list:
            print(f"🔍 Buscando videos de TikTok con: {keyword}")
            search_url = f"https://www.tiktok.com/search/video?q={keyword.replace(' ', '%20')}"
            self.driver.get(search_url)
            time.sleep(5)  # Reducido para rapidez, pero suficiente

            # Scroll optimizado
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(3):  # Reducido para rapidez
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Obtener URLs de videos (selectores actualizados)
            video_urls = []
            seen = set()
            try:
                video_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'DivItemContainer')]//a | //div[contains(@class, 'tiktok-') and contains(@class, 'video')]//a | //a[contains(@href, '/video/') and contains(@href, '/@')]")
                for elem in video_elements:
                    href = elem.get_attribute('href')
                    if href and '/video/' in href and '/@' in href and href not in seen:
                        video_urls.append(href)
                        seen.add(href)
                        if len(video_urls) >= max_videos:
                            break
            except Exception as e:
                print(f"   ⚠️ Error encontrando videos: {e}")

            print(f"   Encontrados {len(video_urls)} videos únicos")

            if not video_urls:
                print("   ⚠️ No se encontraron videos - TikTok puede estar bloqueando")
                continue

            for url in video_urls:
                print(f"   📱 Abriendo video: {url}")
                self.driver.get(url)
                time.sleep(5)  # Reducido

                # Abrir comentarios - método robusto
                opened = False
                try:
                    btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@data-e2e='comment-button'] | //button[@data-e2e='comment-button'] | //button[contains(@aria-label, 'comment') or contains(@aria-label, 'comentario')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", btn)
                    opened = True
                    time.sleep(3)
                except TimeoutException:
                    print("   ⚠️ No se pudo abrir comentarios")
                    continue

                # Scroll en comentarios
                try:
                    container = self.driver.find_element(By.XPATH, "//div[@data-e2e='comment-list'] | //div[contains(@class, 'comment-list')] | //div[contains(@class, 'scroll')]")
                    last_height = self.driver.execute_script("return arguments[0].scrollHeight", container)
                    for _ in range(5):  # Más scroll para más comentarios
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", container)
                        time.sleep(2)
                        new_height = self.driver.execute_script("return arguments[0].scrollHeight", container)
                        if new_height == last_height:
                            break
                        last_height = new_height
                except:
                    pass

                # Extraer comentarios
                try:
                    comments = self.driver.find_elements(By.XPATH, "//div[@data-e2e='comment-item'] | //div[@data-e2e='comment-level-1'] | //div[contains(@class, 'comment-item')]")
                    count = 0
                    for c in comments:
                        if count >= max_comments_per_video:
                            break
                        try:
                            texto = c.find_element(By.XPATH, ".//p | .//span[contains(@class, 'text')] | .//div[contains(@class, 'comment-text')]").text
                            autor = c.find_element(By.XPATH, ".//span[contains(@class, 'username')] | .//a[contains(@href, '@')]").text
                            if texto.strip() and len(texto.strip()) > 10:
                                todos_comentarios.append({
                                    "contenido": texto.strip(),
                                    "autor": autor.strip() or "Anónimo",
                                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                                    "url": url,
                                    "tipo": "tiktok_comment"
                                })
                                count += 1
                        except:
                            continue
                    print(f"   ✅ {count} comentarios extraídos")
                except Exception as e:
                    print(f"   ⚠️ Error extrayendo comentarios: {e}")

        return todos_comentarios

    def cerrar(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("🔻 Navegador Edge cerrado (TikTok)")