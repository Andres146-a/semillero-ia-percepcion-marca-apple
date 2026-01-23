# scrapers/scraper_x.py
import asyncio
import os
from dotenv import load_dotenv
from twscrape import API, gather

load_dotenv()
class ScraperX:
    def __init__(self):
        self.api = API()          # Cliente twscrape
        self._initialized = False  # 🔒 Evita login repetido

    async def setup(self):
        # 🚫 Evita reloguear en cada keyword
        if self._initialized:
            return

        username = os.getenv("X_USERNAME")
        password = os.getenv("X_PASSWORD")
        email = os.getenv("X_EMAIL")        # Opcional
        email_pass = os.getenv("X_EMAIL_PASS")  # Opcional

        if username and password:
            await self.api.pool.add_account(
                username,
                password,
                email or "",
                email_pass or ""
            )
            await self.api.pool.login_all()
            self._initialized = True
            print("✅ Login exitoso con twscrape")
        else:
            print("⚠️ Credenciales X no encontradas en .env")

    async def scrape_comentarios_keywords(self, keywords, max_posts=5, max_replies_per_post=30):
        await self.setup()  # ✅ Ahora solo se ejecuta UNA vez

        query = keywords if isinstance(keywords, str) else " ".join(keywords)
        todos_datos = []
        seen_urls = set()   # 🔁 Evitar duplicados

        tweets = await gather(self.api.search(query, limit=max_posts))

        for tweet in tweets:
            # 🧹 Filtro de texto basura
            if not tweet.rawContent or len(tweet.rawContent.strip()) < 15:
                continue
            if tweet.url in seen_urls:
                continue

            seen_urls.add(tweet.url)

            todos_datos.append({
                "contenido": tweet.rawContent.strip(),
                "autor": tweet.user.username,
                "fecha": tweet.date.isoformat(),
                "url": tweet.url,
                "tipo": "x_tweet"
            })

            replies = await gather(self.api.replies(tweet.id, limit=max_replies_per_post))
            for reply in replies:
                if not reply.rawContent or len(reply.rawContent.strip()) < 15:
                    continue
                if reply.url in seen_urls:
                    continue

                seen_urls.add(reply.url)

                todos_datos.append({
                    "contenido": reply.rawContent.strip(),
                    "autor": reply.user.username,
                    "fecha": reply.date.isoformat(),
                    "url": reply.url,
                    "tipo": "x_reply"
                })

        print(f"✅ Extraídos {len(todos_datos)} elementos (tweets + replies) para '{query}'")
        return todos_datos

    def scrape_sync(self, keywords, max_posts=5, max_replies_per_post=30):
        """Versión síncrona para usar en main"""
        try:
            return asyncio.run(
                self.scrape_comentarios_keywords(
                    keywords,
                    max_posts,
                    max_replies_per_post
                )
            )
        except RuntimeError as e:
            if "running event loop" in str(e):
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(
                    self.scrape_comentarios_keywords(
                        keywords,
                        max_posts,
                        max_replies_per_post
                    )
                )
            else:
                raise e
