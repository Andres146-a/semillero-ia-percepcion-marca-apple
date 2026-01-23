import requests
import time
from datetime import datetime

class ScraperReddit:
    def __init__(self, delay=3):
        self.delay = delay
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0 Safari/537.36"
        }

    def scrape_subreddit(self, subreddit, query, limit=10):
        """
        Versión mejorada: saca COMENTARIOS (replies) de posts relevantes,
        no solo títulos/selftext. Más opiniones reales y menos ruido.
        """
        resultados = []
        after = None
        pages = max(1, limit // 5)  # Más páginas para más posts

        for _ in range(pages):
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                "q": query,
                "restrict_sr": 1,
                "sort": "relevance",
                "t": "year",
                "limit": 25,  # Subimos de 10 a 25 posts por página
                "after": after
            }

            try:
                r = requests.get(url, headers=self.headers, params=params, timeout=15)
                if r.status_code != 200:
                    print(f"⚠️ Reddit HTTP {r.status_code} en r/{subreddit}")
                    break

                data = r.json()
                posts = data.get("data", {}).get("children", [])
                if not posts:
                    break

                for post in posts:
                    p = post["data"]
                    post_permalink = p.get('permalink', '')
                    if not post_permalink:
                        continue

                    # === NUEVO: Scrapeamos los comentarios del post ===
                    comments_url = f"https://www.reddit.com{post_permalink}.json"
                    try:
                        r_comments = requests.get(comments_url, headers=self.headers, timeout=15)
                        if r_comments.status_code != 200:
                            continue

                        comments_data = r_comments.json()
                        # comments_data[1] contiene los comentarios (el [0] es el post)
                        if len(comments_data) < 2:
                            continue

                        comments_tree = comments_data[1].get("data", {}).get("children", [])

                        for comment_item in comments_tree:
                            if comment_item["kind"] != "t1":  # Solo comentarios reales
                                continue
                            comment = comment_item["data"]
                            body = comment.get("body", "").strip()
                            if len(body) < 25:  # Filtro anti-ruido
                                continue

                            resultados.append({
                                "texto": body[:2000],
                                "url": f"https://reddit.com{comment.get('permalink', '')}",
                                "fuente": "reddit",
                                "plataforma": "reddit",
                                "subreddit": subreddit,
                                "autor": comment.get("author", "[deleted]"),
                                "score": comment.get("score", 0),
                                "fecha": datetime.fromtimestamp(comment.get("created_utc", 0)).isoformat()
                            })

                            # Límite por post para no saturar
                            if len(resultados) >= 200:  # Puedes subir a 300-500
                                return resultados

                    except Exception as e:
                        print(f"Error scrapeando comentarios de post {post_permalink}: {e}")
                        continue

                after = data.get("data", {}).get("after")
                if not after:
                    break

                time.sleep(self.delay + 2)  # Delay más largo por doble request

            except Exception as e:
                print(f"❌ Error Reddit ({subreddit}): {e}")
                break

        return resultados
