# scrapers/scraper_youtube.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from datetime import datetime

class ScraperYouTube:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def scrape_comentarios_video(self, video_id, max_results=100):
        """Scrapea comentarios de un video de YouTube"""
        comentarios = []
        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=max_results,
                order="relevance"  
            )
            response = request.execute()

            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comentarios.append({
                    "contenido": comment['textOriginal'],
                    "autor": comment['authorDisplayName'],
                    "fecha": comment['publishedAt'],
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "tipo": "youtube_comment"
                })

            print(f"✅ Extraídos {len(comentarios)} comentarios de video {video_id}")
            return comentarios
        except HttpError as e:
            print(f"Error YouTube API: {e}")
            return []

    def scrape_comentarios_keywords(self, keywords, max_videos=20, max_comments_per_video=50):
        """Busca videos por keywords y scrapea comentarios"""
        todos_comentarios = []
        try:
            search_request = self.youtube.search().list(
                q=keywords,
                part="id,snippet",
                maxResults=max_videos,
                type="video"
            )
            search_response = search_request.execute()

            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                comentarios = self.scrape_comentarios_video(video_id, max_comments_per_video)
                todos_comentarios.extend(comentarios)

            return todos_comentarios
        except HttpError as e:
            print(f"❌ Error YouTube API: {e}")
            return []