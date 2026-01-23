# rag_manager.py (versión mejorada)
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

analyzer = SentimentIntensityAnalyzer() 

class RAGManager:
    def __init__(self, persist_directory="chroma_db_percepcion"):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = Chroma(
            collection_name="comentarios_apple",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
        print(f"✅ Base RAG cargada. Total comentarios almacenados: {self.vectorstore._collection.count()}")

    def agregar_comentarios(self, comentarios, batch_size=1000):
        """
        Agrega comentarios en lotes para evitar errores de tamaño de batch
        """
        if not comentarios:
            print("⚠️ No hay comentarios para agregar")
            return
        
        texts = []
        metadatas = []
        
        print(f"📊 Procesando {len(comentarios)} comentarios...")
        
        # Contadores
        total_validos = 0
        contador_filtrados = 0
        
        for c in comentarios:
            contenido = c.get('contenido', '') or c.get('texto', '')
            
            # Filtro de longitud (más permisivo)
            if len(contenido.strip()) < 20:  # De 50 a 20 caracteres
                contador_filtrados += 1
                continue
            
            # Cálculo de sentiment
            sentiment_score = analyzer.polarity_scores(contenido)
            compound = sentiment_score['compound']
            sentiment_label = "positivo" if compound > 0.05 else "negativo" if compound < -0.05 else "neutral"
            
            # Filtro de tipo (más flexible)
            if c.get("tipo") != "opinion":
                # Pero aceptamos algunos informativos si son relevantes
                palabras_apple = ['apple', 'iphone', 'mac', 'ipad', 'airpods', 'ios']
                if not any(palabra in contenido.lower() for palabra in palabras_apple):
                    contador_filtrados += 1
                    continue
            
            texts.append(contenido.strip())
            metadatas.append({
                "titulo": c.get("titulo", "Sin título"),
                "autor": c.get("autor", "Anónimo"),
                "fecha": c.get("fecha", datetime.now().strftime("%Y-%m-%d")),
                "url": c.get("url", "Desconocida"),
                "plataforma": c.get("plataforma", "desconocida"),
                "fuente_tipo": c.get("fuente_tipo", "desconocida"),
                "tipo": c.get("tipo", "desconocido"),
                "fecha_agregado": datetime.now().isoformat(),
                "sentiment_score": compound,
                "sentiment_label": sentiment_label,
                "longitud": len(contenido)
            })
            
            total_validos += 1
            
            # Agregar en lotes para evitar error de batch size
            if len(texts) >= batch_size:
                print(f"  📦 Agregando lote de {len(texts)} documentos...")
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
                self.guardar()
                print(f"  ✅ Lote agregado. Total acumulado: {self.get_total_documents()}")
                
                # Reiniciar listas
                texts = []
                metadatas = []
        
        # Agregar los restantes (si hay)
        if texts:
            print(f"  📦 Agregando lote final de {len(texts)} documentos...")
            self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
            self.guardar()
        
        print(f"✅ Proceso completado:")
        print(f"   • Comentarios procesados: {len(comentarios)}")
        print(f"   • Válidos agregados: {total_validos}")
        print(f"   • Filtrados: {contador_filtrados}")
        print(f"   • Total en RAG: {self.get_total_documents()} documentos")
                
            
    def guardar(self):
        """Guarda explícitamente el vectorstore en disco"""
        try:
            if hasattr(self.vectorstore, 'persist'):
                self.vectorstore.persist()
                print(f"💾 Vectorstore persistido en: {self.persist_directory}")
            elif hasattr(self.vectorstore, '_persist_directory'):
                # Chroma v0.4+ guarda automáticamente, pero forzamos sync
                import chromadb
                self.vectorstore._client.persist()
                print(f"💾 Chroma persistido en: {self.persist_directory}")
            else:
                print("⚠️ No se pudo persistir: vectorstore no tiene método persist")
        except Exception as e:
            print(f"❌ Error al guardar RAG: {e}")
    def get_sentiment_stats(self):
        """Devuelve estadísticas de sentiment de toda la base"""
        docs = self.vectorstore.get(include=["metadatas"])
        labels = [meta.get("sentiment_label", "neutral") for meta in docs['metadatas']]
        total = len(labels)
        if total == 0:
            return {"positivo": 0, "negativo": 0, "neutral": 0}
        
        from collections import Counter
        count = Counter(labels)
        return {
            "positivo": round(count["positivo"] / total * 100),
            "negativo": round(count["negativo"] / total * 100),
            "neutral": round(count["neutral"] / total * 100)
        }

    def buscar_relevantes(self, query, k=50):
        results = self.vectorstore.similarity_search(query, k=k)
        return results

    def limpiar_base(self):
        self.vectorstore.delete_collection()
        print("✅ Base RAG limpiada completamente")

    def total_comentarios(self):
        return self.vectorstore._collection.count()
    
    def get_total_documents(self):
        """Retorna el número total de documentos en la base vectorial (Chroma)"""
        if hasattr(self, 'vectorstore') and self.vectorstore is not None:
            try:
                return self.vectorstore._collection.count()
            except Exception as e:
                print(f"Error al contar documentos: {e}")
                return 0
        return 0
    def print_stats(self):
        total = self.get_total_documents()
        print(f"Total documentos en RAG: {total}")
        print(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}")