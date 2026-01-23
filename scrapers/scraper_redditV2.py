import praw
from datetime import datetime

class ScraperReddit:
    def __init__(self, client_id, client_secret, user_agent="percepcion_apple:v1"):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )

    def scrape_subreddit(self, subreddit_name, query="", limit_posts=30, max_comments_per_post=100):
        comentarios = []
        sub = self.reddit.subreddit(subreddit_name)

        # Busca posts relevantes
        posts = sub.search(query, limit=limit_posts) if query else sub.hot(limit=limit_posts)

        for post in posts:
            post.comments.replace_more(limit=None)  # Carga todas las replies
            for comment in post.comments.list():
                if len(comment.body) < 20:
                    continue
                comentarios.append({
                    "texto": comment.body.strip(),
                    "autor": str(comment.author) if comment.author else "[deleted]",
                    "score": comment.score,
                    "url": f"https://reddit.com{comment.permalink}",
                    "plataforma": "reddit",
                    "subreddit": subreddit_name,
                    "fecha": datetime.fromtimestamp(comment.created_utc).isoformat()
                })
                if len(comentarios) >= max_comments_per_post * limit_posts:
                    return comentarios[:max_comments_per_post * limit_posts]

        return comentarios