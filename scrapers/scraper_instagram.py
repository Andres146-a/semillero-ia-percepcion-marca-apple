import instaloader
import time
import os
from dotenv import load_dotenv
from datetime import datetime
import time 

load_dotenv()

class ScraperInstagram:
    def __init__(self):
        self.L = instaloader.Instaloader()
        
        username = os.getenv("INSTAGRAM_USERNAME")
        if username:
            session_file = f"session-{username}"
            if os.path.exists(session_file):
                try:
                    self.L.load_session_from_file(username)
                    print("✅ Sesión Instagram cargada desde archivo")
                except:
                    print("⚠️ Sesión corrupta. Login nuevo.")
                    self._login_new()
            else:
                self._login_new()
        else:
            print("⚠️ Sin credenciales")

    def _login_new(self):
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        if username and password:
            try:
                self.L.login(username, password)
                self.L.save_session_to_file(username)
                print("✅ Login nuevo y sesión guardada")
                time.sleep(30)  # Delay largo después de login
            except Exception as e:
                print(f"❌ Error login: {e}")

    def scrape_comments_profile(self, username, max_posts=2, max_comments_per_post=10):
        datos = []
        try:
            print(f"   Buscando perfil @{username}...")
            profile = instaloader.Profile.from_username(self.L.context, username)
            time.sleep(20)  # Delay antes de cargar posts
            
            posts_contados = 0
            for post in profile.get_posts():
                if posts_contados >= max_posts:
                    break
                
                time.sleep(15)  # Delay muy largo entre posts
                
                comentarios_contados = 0
                for comment in post.get_comments():
                    if comentarios_contados >= max_comments_per_post:
                        break
                    time.sleep(2)
                    datos.append({
                        "contenido": comment.text,
                        "autor": comment.owner.username,
                        "fecha": comment.created_at_utc.isoformat(),
                        "url": f"https://www.instagram.com/p/{post.shortcode}/",
                        "tipo": "instagram_comment"
                    })
                    comentarios_contados += 1
                
                posts_contados += 1
            
            print(f"✅ Extraídos {len(datos)} comentarios del perfil @{username}")
            return datos
        except instaloader.exceptions.QueryReturnedNotFoundException:
            print(f"⚠️ Perfil @{username} no encontrado o privado")
            return []
        except instaloader.exceptions.ConnectionException as e:
            if "401" in str(e) or "rate" in str(e).lower():
                print(f"⚠️ Rate limit en @{username}. Espera 30-60 minutos y reintenta.")
            else:
                print(f"❌ Error conexión @{username}: {e}")
            return []
        except Exception as e:
            print(f"❌ Error en @{username}: {e}")
            return []