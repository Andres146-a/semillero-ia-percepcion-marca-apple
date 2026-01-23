from youtube_comment_downloader import YoutubeCommentDownloader
import time
import yt_dlp

class ScraperYouTube:
    def __init__(self):
        self.downloader = YoutubeCommentDownloader()
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Solo IDs, más rápido
            'skip_download': True
        }

    def scrape_comentarios_video(self, video_id: str, max_comments: int = 300):
        comentarios = []
        try:
            raw_comments = self.downloader.get_comments_from_url(
                f"https://www.youtube.com/watch?v={video_id}",
                sort_by=0  # 0 = más populares primero
            )
            count = 0
            for comment in raw_comments:
                if count >= max_comments:
                    break
                texto = comment.get('text', '').strip()
                if len(texto) < 15:
                    continue
                comentarios.append({
                    "texto": texto,
                    "autor": comment.get('author', 'Anónimo'),
                    "likes": comment.get('votes', 0),
                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment.get('cid', '')}",
                    "plataforma": "youtube",
                    "video_id": video_id
                })
                count += 1
            # Pequeño delay para ser amable con YouTube
            time.sleep(0.5)
        except Exception as e:
            print(f"Error scrapeando comentarios de {video_id}: {e}")
        return comentarios

    def buscar_video_ids(self, query: str, limit: int = 10):
        """Busca video IDs con yt-dlp de forma segura"""
        if not query.strip():
            print("   ⚠️ Keyword vacío, saltando")
            return []
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                search_query = f"ytsearch{limit}:{query}"
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries', [])
                if not entries:
                    print(f"   ⚠️ No se encontraron videos para: '{query}'")
                    return []
                video_ids = [entry['id'] for entry in entries if entry.get('id')]
                print(f"   Encontrados {len(video_ids)} videos para: '{query}'")
                return video_ids
        except Exception as e:
            print(f"Error en búsqueda yt-dlp para '{query}': {e}")
            return []

    def scrape_comentarios_keywords(self, keywords_list, max_videos_per_kw=6, max_comments_per_video=60):
        todos = []
        for kw in keywords_list:
            kw = kw.strip()
            if not kw:
                continue
            print(f"\nBuscando videos para: '{kw}'")
            video_ids = self.buscar_video_ids(kw, limit=max_videos_per_kw * 2)  # Busca más para filtrar
            if not video_ids:
                continue

            for vid in video_ids[:max_videos_per_kw]:
                print(f"   Scrapeando comentarios de video: {vid}")
                comentarios = self.scrape_comentarios_video(vid, max_comments_per_video)
                todos.extend(comentarios)
                print(f"   +{len(comentarios)} comentarios extraídos")
                time.sleep(2)  # Respeto a YouTube

        return todos