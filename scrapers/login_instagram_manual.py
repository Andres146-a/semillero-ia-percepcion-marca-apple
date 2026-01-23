# login_instagram_manual.py
import instaloader
import os
from dotenv import load_dotenv

load_dotenv()

L = instaloader.Instaloader()

username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")

L.login(username, password)  # Si pide código 2FA, te lo pregunta en consola
L.save_session_to_file(username)  # Guarda sesión en archivo

print("✅ Sesión guardada. Ahora puedes usar sin login repetido.")