# main_integrado.py
import sys
from langchain_openai import OpenAIEmbeddings
import ollama
import json
import matplotlib
from datetime import datetime
from dotenv import load_dotenv
from rapidfuzz import fuzz, process
from ragas.testset.generator import TestsetGenerator
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from utils.visualizacion import generar_pie_sentiment, generar_wordcloud


from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

#from scrapers.scraper_youtube import ScraperYouTube
#from scrapers.scraper_redditV2 import ScraperReddit
from scrapers.scraper_yotubeV2 import ScraperYouTube
from scrapers.scraper_reddit import ScraperReddit

from rag.rag_manager import RAGManager
from scrapers.scraper_hibrido import ScraperHibrido
from utils.downloader import DescargadorInteligente
from processors.normalizador import NormalizadorMVP


# Importar tu sistema existente
sys.path.append('.')
# Cargar variables de entorno
load_dotenv()
matplotlib.use('Agg')

# Configuración del modelo Ollama
MODELO_OLLAMA = "llama3.1:8b"




def analizar_con_ollama(rag_manager, stats=None, query="percepción general de Apple", modo="reporte", modelo=MODELO_OLLAMA):
    print("Buscando comentarios relevantes en RAG")
    docs = rag_manager.buscar_relevantes(query, k=100 if modo == "reporte" else 100)
    print(f"→ Recuperados {len(docs)} documentos (k=100)")

    # Deduplicación rápida por contenido (elimina comentarios idénticos)
    unique_docs = []
    seen_texts = set()
    for doc in docs:
        text = doc.page_content.strip()
        if text not in seen_texts:
            seen_texts.add(text)
            unique_docs.append(doc)

    docs = unique_docs

    print(f"→ Después de dedup básico: {len(docs)} únicos")

    try:
        def dedup_fuzzy_retrieval(docs_list, threshold=88):
            texts = [d.page_content.strip() for d in docs_list]
            unique = []
            used = set()
            for i, txt in enumerate(texts):
                if i in used: continue
                unique.append(docs_list[i])
                if i + 1 < len(texts):
                    matches = process.extract(txt, texts[i+1:], scorer=fuzz.token_sort_ratio, limit=None)
                    for _, score, idx in matches:
                        if score >= threshold:
                            used.add(i + 1 + idx)
            return unique

        docs = dedup_fuzzy_retrieval(docs)
        print(f"→ Después de fuzzy en retrieval: {len(docs)} únicos")
    except:
        pass
    

    # Deduplicación semántica (elimina comentarios muy similares)
    try:
        embeddings = rag_manager.embeddings.embed_documents([d.page_content for d in docs])
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        unique_sem = []
        used_sem = set()
        for i, emb in enumerate(embeddings):
            if i in used_sem: continue
            unique_sem.append(docs[i])
            sims = cosine_similarity([emb], embeddings[i+1:])[0]
            for j, s in enumerate(sims):
                if s >= 0.90:  
                    used_sem.add(i + 1 + j)

        docs = unique_sem
        print(f"→ Después semántica (threshold 0.90): {len(docs)} únicos")
    except Exception as e:
        print(f"⚠️ Semántica falló: {e}")
        
        
    # Se usa Reranking con Cross-Encoder para mejorar relevancia
    try:
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')  # Modelo ligero y efectivo

        # Pares: (query, doc_text)
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.predict(pairs)

        # Reordena por score descendente
        sorted_indices = np.argsort(scores)[::-1]
        docs = [docs[i] for i in sorted_indices]

        print(f"→ Después reranking: {len(docs)} docs reordenados por relevancia")
    except Exception as e:
        print(f"⚠️ Reranking falló: {e}")
  

    print(f"→ Después de deduplicación: {len(docs)} documentos únicos")

    # Limita a un número razonable para Ollama (evita prompt demasiado largo)
    docs = docs[:150]
    if stats is None:
        stats = {"positivo": 0, "negativo": 0, "neutral": 0}
    if not docs:
        return {"error": "No se encontraron comentarios relevantes"}
    
    textos_comentarios = "\n\n".join([
    f"Comentario relevante #{i+1} (plataforma: {doc.metadata.get('plataforma', 'desconocida')}, fuente: {doc.metadata.get('fuente_tipo', 'desconocida')}):\n"
    f"{doc.page_content.strip()[:800]}\n"
    f"URL: {doc.metadata.get('url', 'N/A')}\n"
    for i, doc in enumerate(docs)
])
    
    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    if modo == "reporte":
        prompt = f"""
    Eres un analista profesional de percepción de marca.

    REGLAS:
    - Responde SOLO con JSON válido. Nada más. Empieza con {{ y termina con }}.
    - Usa SOLO los comentarios abajo.
    - Llena TODOS los campos aunque la evidencia sea débil o minoritaria (usa "Algunos usuarios mencionan...", "Existe cierta crítica sobre...").
    - Si no hay suficiente para un campo, escribe "No hay evidencia clara" pero no lo dejes vacío.
    - Prioriza repeticiones, pero incluye tendencias aunque sean pocas.
    - No copies texto literal.

    JSON EXACTO:

    {{
    "fecha_analisis": "{fecha_actual}",
    "total_comentarios_analizados": {len(docs)},
    "percepcion_general": "frase resumen (obligatorio)",
    "sentimiento_general": {{ "positivo": {stats.get("positivo", 0)}, "negativo": {stats.get("negativo", 0)}, "neutral": {stats.get("neutral", 0)} }},
    "fortalezas": ["1 o más frases cortas (no dejar vacío si hay algo positivo)"],
    "debilidades": ["1 o más frases cortas (no dejar vacío si hay algo negativo)"],
    "problemas_frecuentes": ["problema 1 o 'ninguno claro'"],
    "tendencias_emergentes": ["tendencia 1 o 'ninguna clara'"],
    "resumen_ejecutivo": "2-4 oraciones (obligatorio, aunque sea breve)"
    }}

    Si no puedes: {{"error": "No se pudo generar"}}

    Comentarios:
    {textos_comentarios}
    """

    else:  # modo = "pregunta"
        prompt = f"""
    Eres un analista de percepción de marca Apple.

    Tu respuesta DEBE basarse EXCLUSIVAMENTE en los comentarios recuperados del RAG.
    NO uses conocimiento externo ni generalices más allá de lo que aparece en los textos.

    REGLAS ESTRICTAS:
    - Basate exclusivamente en los comentarios proporcionados abajo.
    - Si un tema tiene muchas menciones → descríbela como patrón común ("muchos usuarios dicen...", "la mayoría percibe...")
    - Si aparece en pocos comentarios → di "algunos usuarios mencionan..."
    - Si NO aparece o hay muy poca evidencia → responde: "No hay evidencia suficiente en los comentarios analizados para concluir sobre este tema."
    - Puedes describir patrones con ejemplos genéricos (sin copiar texto literal completo): "varios usuarios se quejan del precio alto", "muchos destacan la fluidez del sistema".
    - NO inventes temas ni afirmaciones que no estén respaldadas por los comentarios.
    - Si el usuario pide comentarios textuales exactos → di: "Por política de privacidad y para proteger el anonimato, no comparto citas textuales literales. Puedo describir patrones y tendencias generales."

    Comentarios disponibles ({len(docs)} recuperados para esta pregunta):
    {textos_comentarios}

    Pregunta del usuario: {query}

    Responde de forma clara, objetiva y fiel a los datos.
    NOTA IMPORTANTE SOBRE LA BASE DE DATOS:
    - En la base completa hay aproximadamente {rag_manager.get_total_documents()} comentarios recopilados.
    - Aquí te estoy pasando solo los {len(docs)} más relevantes y únicos para esta pregunta.
    - Responde basado exclusivamente en los comentarios que te doy, pero puedes mencionar si el tema parece común o raro en el conjunto total.
    
    """


    try:
        response = ollama.generate(model=modelo, prompt=prompt)
        resultado_texto = response['response'].strip()

        import re
        resultado_texto = re.sub(r'^```json\s*|\s*```$', '', resultado_texto, flags=re.MULTILINE).strip()

        if modo == "reporte":
            json_match = re.search(r'\{.*\}', resultado_texto, re.DOTALL)
            json_str = json_match.group(0) if json_match else resultado_texto
            try:
                reporte = json.loads(json_str)
                if isinstance(reporte, list) and len(reporte) > 0:
                    reporte = reporte[0]
                # Normalizar estructura mínima
                reporte.setdefault("fecha_analisis", fecha_actual)
                reporte.setdefault("total_comentarios_analizados", len(docs))
                reporte.setdefault("percepcion_general", "No disponible")
                reporte.setdefault("sentimiento_general", {"positivo": 0, "negativo": 0, "neutral": 0})
                reporte.setdefault("fortalezas", [])
                reporte.setdefault("debilidades", [])
                reporte.setdefault("resumen_ejecutivo", "No disponible")

                print("✅ Reporte JSON parseado correctamente")
            except json.JSONDecodeError as e:
                print(f"⚠️ Error parseando JSON: {e}")
                reporte = {"error": "JSON inválido", "texto_crudo": resultado_texto}
            
            # Guardar reporte
            filename = f"reporte_percepcion_apple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(reporte, f, ensure_ascii=False, indent=2)
            print(f"✅ Reporte guardado: {filename}")
            return reporte
        else:
            # Modo pregunta: respuesta en texto natural
            return {"respuesta_texto": resultado_texto}

    except Exception as e:
        print(f"❌ Error con Ollama: {e}")
        return {"error": str(e)}

def inferir_fuente(item):
    fuente = (
        item.get("fuente")
        or item.get("url")
        or item.get("plataforma")
        or ""
    ).lower()

    if "youtube" in fuente:
        return "youtube", "red_social"
    if "reddit" in fuente:
        return "reddit", "foro"
    if "twitter" in fuente or "x.com" in fuente:
        return "x", "red_social"
    if "tiktok" in fuente:
        return "tiktok", "red_social"
    if "macrumors" in fuente:
        return "macrumors", "foro"
    if "forum" in fuente:
        return "foro", "foro"

    return "web", "blog"



def clasificar_texto(texto: str) -> str:
    """
    Clasificador más relajado y efectivo.
    Prioriza detectar cualquier opinión (positiva o negativa) sobre informativo/ruido.
    """
    texto_l = texto.lower().strip()

    # 1. Umbral más bajo: comentarios de 15+ caracteres pueden ser válidos
    if len(texto_l) < 15:
        return "ruido"

    # Palabras clave fuertes de opinión/queja (ampliamos mucho, español + inglés)
    palabras_opinion_fuerte = [
        # Español
        "me gusta", "no me gusta", "odio", "amo", "prefiero", "recomiendo",
        "vale la pena", "no vale la pena", "caro", "carísimo", "barato",
        "increíble", "decepcionante", "frustrante", "problema", "bug",
        "fallo", "error", "defecto", "genial", "perfecto", "horrible",
        "cambié", "dejé", "regreso", "nunca más", "para siempre",
        # Inglés (por si hay comentarios mixtos)
        "love", "hate", "amazing", "disappointing", "overpriced", "worth it",
        "regret", "best", "worst", "issue", "bug", "problem"
    ]

    # Frases indicadoras de experiencia personal
    frases_personales = [
        "yo ", "mi iphone", "mi mac", "en mi caso", "para mí", "en mi experiencia",
        "tengo un", "compré", "uso un", "mi experiencia", "después de usar",
        "llevo", "meses con", "años con", "mi opinión", "opino que"
    ]

    # Si tiene cualquiera de estas → opinión (positiva o negativa)
    if any(palabra in texto_l for palabra in palabras_opinion_fuerte):
        return "opinion"

    if any(frase in texto_l for frase in frases_personales):
        return "opinion"

    # Solo si parece puramente informativo lo marcamos como tal
    palabras_informativas = [
        "lanzamiento", "presentado", "características", "especificaciones",
        "precio oficial", "disponible en", "se filtra", "rumor"
    ]
    if any(p in texto_l for p in palabras_informativas):
        return "informativo"

    # Por defecto: si pasa el filtro de longitud, lo consideramos opinión potencial
    return "opinion"


def responder_con_stats(stats_globales, fuentes_stats):
    print("\n📊 MÉTRICAS DE FUENTES")

    total = sum(fuentes_stats.values())

    for fuente, total_fuente in fuentes_stats.items():
        pct = round(total_fuente * 100 / total, 1) if total > 0 else 0
        print(f"- {fuente}: {total_fuente} ({pct}%)")

def es_opinion_real(texto: str) -> bool:
    """
    Filtro final ultra-relajado.
    Solo descarta si es claramente ruido o propaganda.
    """
    texto_l = texto.lower()

    # Umbral muy bajo: 12 caracteres mínimo
    if len(texto_l) < 12:
        return False

    # Descartar solo cosas muy obvias de ruido
    ruido_obvio = [
        "suscríbete", "dale like", "activa la campanita",
        "gracias por ver", "comentario fijado", "primer",
        "https://", "www.", "@", "giveaway", "sorteo"
    ]
    if any(r in texto_l for r in ruido_obvio):
        return False

    # Si tiene al menos una palabra emocional o personal → opinión real
    palabras_emocionales = [
        "bueno", "malo", "mejor", "peor", "caro", "barato",
        "gusta", "odio", "amo", "increíble", "horrible",
        "problema", "genial", "perfecto", "decepcion"
    ]
    if any(p in texto_l for p in palabras_emocionales):
        return True

    # Si menciona productos Apple directamente + verbo → casi siempre opinión
    productos = ["iphone", "mac", "ipad", "watch", "airpods", "ios", "macos", "apple"]
    verbos = ["es", "tiene", "funciona", "vale", "cuesta", "dura"]
    if any(prod in texto_l for prod in productos) and any(v in texto_l for v in verbos):
        return True

    # Por defecto: aceptamos (relajado máximo)
    return True



def main():
    global scraper
    global x_scraper
    print("""
    ========================================
    🤖 SISTEMA INTEGRADO: SCRAPING + OLLAMA + RAG (LOCAL)
    ========================================
    """)

    print("🔧 Inicializando componentes...")
    
    print("📁 Configurando RAGManager...")
    
    # === SOLO UNA INICIALIZACIÓN DEL RAG ===
    persist_dir = "./apple_sentiment_db"  # Directorio único y consistente
    print(f"📁 Configurando RAGManager en: {persist_dir}")
    
    #Creación de memoria:
    llm = Ollama(model=MODELO_OLLAMA, temperature=0.1)
    # Memoria con resumen automático (mantiene ~2000-3000 tokens aprox)
    memory = ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit=3600,           # ajusta según tu hardware
        memory_key="chat_history",
        return_messages=True
    )
    question_prompt = PromptTemplate(
            input_variables=["chat_history", "question", "context"],
            template="""
        Eres un analista experto en percepción de marca.
        Usa SOLO la información de los comentarios recuperados y el historial de conversación.

        Historial de conversación anterior:
        {chat_history}

        Contexto recuperado del RAG (comentarios relevantes):
        {context}

        Pregunta actual del usuario: {question}

        Responde de forma clara, objetiva y fiel a los datos.
        Si el tema no aparece en el contexto ni en el historial → di "No hay suficiente información en los datos analizados".
        """
    )

    # Cadena para responder preguntas (con memoria)
    chain = (
        RunnablePassthrough.assign(
            chat_history=lambda x: memory.load_memory_variables({})["chat_history"]
        )
        | question_prompt
        | llm
        | StrOutputParser()
    )
    
    # Inicializa RAGManager UNA SOLA VEZ
    rag = RAGManager(persist_directory=persist_dir)
    print(f"✅ RAG inicializado. Documentos actuales: {rag.get_total_documents()}")
    
    # Inicializa scrapers
    descargador = DescargadorInteligente(delay_min=4, delay_max=7)
    normalizador = NormalizadorMVP()
    scraper = ScraperHibrido(descargador, normalizador)
    youtube_scraper = ScraperYouTube()
    reddit_scraper = ScraperReddit()



    print("\n🚀 FASE 1: Web Scraping + YouTube")
    print("=" * 40)

    # INICIALIZAR lista vacía ANTES de cualquier scraping

    todos_datos = []

    # 1. Scraping web tradicional
    urls = [
    # Blogs con comunidad activa (comentarios)
 


    # Foros (ORO PURO)
    
    "https://forums.macrumors.com/forums/iphone.109/",
    "https://forums.macrumors.com/forums/macbook.115/",
    "https://forums.macrumors.com/forums/apple-watch.130/",
    "https://forums.macrumors.com/forums/ipad.122/",
]


    for i, url in enumerate(urls, 1):
        print(f"\n📄 [{i}/{len(urls)}] Scrapeando web: {url}")
        datos = scraper.scrape(url)
        if datos:
            todos_datos.extend(datos)
            print(f"   ✅ Extraídos {len(datos)} elementos web")
   
    
   
    # 2. Scraping YouTube
    print("\n🚀 FASE 1.5: Scraping YouTube Comments")
    print("=" * 40)

    youtube_keywords = [
    # Reviews reales
    "iPhone 16 review español",
    "iPhone 16 opinión sincera",
    "MacBook Pro M4 review",
    "Apple Watch Series 10 opiniones",
    "iPhone 16 problemas reales",
    "iOS 18 bugs español",
    "Apple caro vale la pena",
    "por qué dejé Apple",
    "ecosistema Apple atrapado",
    "MacBook M4 fallos",
    "Apple no innova 2025"
    # Experiencia real
    "iPhone 16 después de un mes",
    "MacBook Pro M4 uso profesional",
    "Apple ecosistema experiencia real",

    # Unboxing / emoción
    "unboxing iPhone 16 español",
    "AirPods Pro 2 unboxing",
    "primera impresión Apple Vision Pro",

    # Problemas reales
    "iOS 18 problemas reales",
    "iPhone 16 problemas comunes",
    "iCloud problemas usuarios",

    # Comparaciones
    "iPhone vs Samsung experiencia",
    "MacBook vs Windows experiencia real",

    # Servicios
    "Apple Music vs Spotify opinión",
    "Apple TV Plus opiniones reales",

    # Marca / percepción
    "por qué la gente ama Apple",
    "Apple sobrevalorado opinión",
    "Apple caro vale la pena"
]


    comentarios_yt = youtube_scraper.scrape_comentarios_keywords(
        keywords_list=youtube_keywords,
        max_videos_per_kw=4,          # 8 videos por keyword
        max_comments_per_video=10     # Hasta 100 comentarios por video
    )

    todos_datos.extend(comentarios_yt)

    total_yt = len(comentarios_yt)
    print(f"\n✅ Total comentarios extraídos de YouTube: {total_yt}")

    if total_yt == 0:
        print("\n⚠️ No se extrajeron comentarios de YouTube. Continuando con otras fuentes...")
    else:
        print(f"   Promedio aproximado por keyword: {total_yt // len(youtube_keywords)} comentarios")

    # Continúa con el resto
    print(f"\n💾 Total elementos scrapeados hasta ahora: {len(todos_datos)} (web + YouTube)")
    print("\n🚀 FASE 1.6: Scraping TikTok Comments")
    print("=" * 40)


    """
    #Aun no se utiliza debido a limitaciones con la Api de TikTok y bloqueos frecuentes.
    print("\n🚀 FASE 1.6: Scraping TikTok Comments (unofficial API)")
    print("=" * 40)

    tiktok_keywords = [
        "iPhone 16 review español",
        "AirPods Pro 2 unboxing",
        "MacBook Pro M4 review",
        "Apple Watch Series 10 opiniones",
        "iOS 18 problemas",
        "Apple Vision Pro análisis"
    ]

    tiktok_comentarios = tiktok_scraper.scrape_comments_keywords(tiktok_keywords, max_videos=2, max_comments_per_video=15)
    todos_datos.extend(tiktok_comentarios)
    tiktok_scraper.cerrar()
 
    """
    print("\n🚀 FASE REDDIT: Scraping Opiniones")
    print("=" * 40)

    subreddits_queries = {
    # Núcleo Apple (opinión + crítica)
    "apple": (
        "Apple experience OR Apple ecosystem worth it OR "
        "Apple overpriced OR Apple disappointed OR leaving Apple"
    ),

    # iPhone (uso real + problemas)
    "iphone": (
        "iPhone experience OR iPhone problems OR "
        "iPhone regret OR iPhone not worth it"
    ),

    # Mac / macOS
    "mac": (
        "MacBook experience OR macOS issues OR "
        "MacBook overpriced OR MacBook regret"
    ),

    # iOS bugs / frustración
    "ios": (
        "iOS problems OR iOS bugs OR "
        "iOS frustrating OR iOS updates broke"
    ),

    # Soporte / quejas directas
    "applehelp": (
        "Apple problem OR Apple issue OR "
        "Apple support bad OR Apple not helping"
    ),

    # Opinión general / consumo
    "gadgets": (
        "Apple review OR Apple opinion OR "
        "Apple overpriced OR Apple not worth it"
    ),

    # Comparación / abandono
    "android": (
        "Apple vs Android OR switching from Apple OR leaving Apple ecosystem"
    ),

    # Comparación profesional
    "windows": (
        "MacBook vs Windows OR leaving MacBook OR switch from Mac"
    )
}




    for sub, query in subreddits_queries.items():
        print(f"   🔍 Scrapeando r/{sub}")
        datos = reddit_scraper.scrape_subreddit(
            subreddit=sub,
            query=query,
            limit=100,  # Máximo 100 posts por subreddit
        )
        if datos:
            todos_datos.extend(datos)
            print(f"   ✅ {len(datos)} comentarios extraídos de r/{sub}")
        else:
            print(f"   ⚠️ Sin resultados en r/{sub}")


   

    print(f"   Total acumulado hasta ahora: {len(todos_datos)} elementos")
   
    unique = {item.get('texto', '').strip(): item for item in todos_datos if item.get('texto')}
    todos_datos = list(unique.values())
    print(f"Después de dedup exacta: {len(todos_datos)} elementos")

    # Ahora la fuzzy (la importante)
 

    def deduplicar_fuzzy(items, threshold=90):
        textos = [item.get('texto', '').strip() for item in items]
        unique = []
        usados = set()

        for i, texto in enumerate(textos):
            if i in usados or not texto:
                continue
            unique.append(items[i])
            if i + 1 < len(textos):
                matches = process.extract(
                    texto,
                    textos[i+1:],
                    scorer=fuzz.token_sort_ratio,
                    limit=None
                )
                for _, score, rel_idx in matches:
                    if score >= threshold:
                        usados.add(i + 1 + rel_idx)

        print(f"Deduplicación fuzzy ({threshold}%): {len(items)} → {len(unique)} elementos")
        return unique

     
    todos_datos = deduplicar_fuzzy(todos_datos, threshold=90)
    print(f"Total después de fuzzy + exacta: {len(todos_datos)} elementos")
    print(f"Reducción por fuzzy: {len(unique) - len(todos_datos)} elementos eliminados")
    """
    # Scraper Instagram
    print("\n🚀 FASE 1.8: Scraping Instagram Comments (perfiles públicos)")
    print("=" * 40)

    # Perfiles públicos con contenido Apple (unboxings, reviews, fans)
    ig_profiles = [
    "mkbhd", 
        ]

    for profile in ig_profiles:
        comments = ig_scraper.scrape_comments_profile(profile, max_posts=1, max_comments_per_post=5)
        todos_datos.extend(comments)
        time.sleep(120)  # Delay entre perfiles para evitar bloqueo total

    # Opcional: perfil oficial de Apple (público)
    comments_apple = ig_scraper.scrape_comments_profile("apple", max_posts=3, max_comments_per_post=20)
    todos_datos.extend(comments_apple)
    
    
    
    
    """
    plataforma_stats = {
    "reddit": 0,
    "youtube": 0,
    "web": 0,
    "x": 0
    }

    stats_pipeline = {
    "total_scrapeados": 0,
    "descartados_ruido": 0,
    "descartados_cortos": 0,
    "validos": 0
    }

    stats_globales = {
    "opinion": 0,
    "informativo": 0
    }

    fuentes_stats = {}
    """
    # Deduplicación por texto exacto
    unique = {item.get('texto', '').strip(): item for item in todos_datos if item.get('texto')}
    def deduplicar_mejorado(items, threshold=92):
        textos = [item.get('texto','').strip() for item in items]
        unique = []
        indices_usados = set()

        for i, texto in enumerate(textos):
            if i in indices_usados:
                continue
            unique.append(items[i])
            # Buscar similares
            matches = process.extract(texto, textos[i+1:], scorer=fuzz.token_sort_ratio)
            for match, score, idx in matches:
                if score >= threshold:
                    indices_usados.add(i + 1 + idx)

        return unique

    # Uso
    todos_datos = deduplicar_mejorado(todos_datos, threshold=90)
    """
    print(f"Después de dedup: {len(todos_datos)} elementos")
    comentarios_validos = []
        # ───────────────────────────────────────────────────────────────
    #          GUARDAR TODOS LOS DATOS SCRAPEADOS PARA INSPECCIÓN
    # ───────────────────────────────────────────────────────────────

    print("\n💾 Guardando datos scrapeados crudos para revisión...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Versión JSON completa y bonita (fácil de abrir con editor o navegador)
    json_path = f"datos_scrapeados_crudos_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(todos_datos, f, ensure_ascii=False, indent=2, default=str)
    print(f"   → JSON completo: {json_path}  ({len(todos_datos):,} elementos)")

    # 2. Versión texto plano muy legible (ideal para revisar con ojos humanos)
    txt_path = f"datos_scrapeados_crudos_{timestamp}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"ARCHIVO DE DATOS SCRAPEADOS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total elementos scrapeados: {len(todos_datos)}\n")
        f.write("=" * 80 + "\n\n")

        for i, item in enumerate(todos_datos, 1):
            f.write(f"┌─── ELEMENTO #{i} ───────────────────────────────────────┐\n")
            
            # Texto principal (el más importante)
            texto = item.get("texto") or item.get("contenido") or item.get("text") or "(sin texto)"
            f.write(f"TEXTO:\n{texto}\n\n")
            
            # Metadatos clave
            campos_interesantes = [
                ("Plataforma", item.get("plataforma") or item.get("source") or "—"),
                ("URL", item.get("url") or item.get("video_url") or "—"),
                ("Autor", item.get("autor") or item.get("author") or item.get("username") or "—"),
                ("Fecha", item.get("fecha") or item.get("date") or item.get("published_at") or "—"),
                ("Tipo", item.get("tipo") or "—")
            ]
            
            for nombre, valor in campos_interesantes:
                if valor and valor != "—":
                    f.write(f"{nombre:12}: {valor}\n")
            
            f.write("└────────────────────────────────────────────────────────────┘\n\n")

    print(f"   → TXT legible: {txt_path}")
    print("   ¡Listo! Abre cualquiera de los dos archivos para revisar los datos crudos.\n")
    
    
   
        
    
    for item in todos_datos:
        stats_pipeline["total_scrapeados"] += 1

        texto = item.get("texto") or item.get("contenido") or item.get("text") or ""
        texto = texto.strip().lower()

        # Filtro 1: Vacíos/cortos
        if not texto or len(texto) < 30:
            stats_pipeline["descartados_cortos"] += 1
            continue

        # Filtro 2: Ruido de headers/menús (patrones específicos de MacRumors/foros)
        ruido_patterns = [
            "got a tip for us", "send us an email", "anonymous form", "front page", "roundups",
            "airpods", "iphone", "macbook", "watchos", "search everywhere", "new posts", "forum list"
        ]
       # if any(pattern in texto for pattern in ruido_patterns) and len(texto) < 500:  # Solo si no es comentario largo
        #    stats_pipeline["descartados_ruido"] += 1
         #   continue

        # Filtro 3: Repeticiones (baja diversidad de palabras)
        palabras = texto.split()
        #if len(palabras) > 0 and len(set(palabras)) / len(palabras) < 0.4:  # <40% únicas → repetitivo
         #   stats_pipeline["descartados_ruido"] += 1
          #  continue

        # Tus filtros existentes (clasificar_texto, es_opinion_real, etc.)
        tipo = clasificar_texto(texto)
        """ 
        if tipo == "ruido":
            stats_pipeline["descartados_ruido"] += 1
            continue
        """
  

        # 🔹 Inferir plataforma ANTES de usarla
        plataforma, fuente_tipo = inferir_fuente(item)
        item["plataforma"] = plataforma
        item["fuente_tipo"] = fuente_tipo

        # 🔹 Conteo por plataforma (TODOS, incluso descartados)
        plataforma_stats[plataforma] = plataforma_stats.get(plataforma, 0) + 1

        # 🔹 Filtros
       # if len(texto) <  30:  # Más permisivo
        #    stats_pipeline["descartados_cortos"] += 1
         #   continue

        tipo = clasificar_texto(texto)
        if tipo == "ruido":
            stats_pipeline["descartados_ruido"] += 1
            continue

        # 🔹 Válidos
        item["tipo"] = tipo
        stats_pipeline["validos"] += 1

        if tipo == "opinion" and es_opinion_real(texto):  # Quitamos "opinion_negativa" restrictivo
            stats_globales["opinion"] += 1
            item["tipo_fuente"] = "opinion_real"
            item["longitud_texto"] = len(texto)
            comentarios_validos.append(item)
        else:
            stats_globales["informativo"] += 1


        # 🔹 Conteo para preguntas tipo “Reddit vs YouTube”
        fuentes_stats[plataforma] = fuentes_stats.get(plataforma, 0) + 1

    total = sum(plataforma_stats.values())

    for plataforma, count in plataforma_stats.items():
        pct = round(count * 100 / total, 1) if total > 0 else 0
        print(f"{plataforma}: {count} ({pct}%)")

     # ───────────────────────────────────────────────────────────────
    #   Preparar datos para Ragas (dataset de evaluación inicial)
    # ───────────────────────────────────────────────────────────────

    print("\n📊 Preparando muestra para evaluación con Ragas...")

    # Usamos comentarios válidos (después de filtrado) para mayor calidad
    # Si quieres usar TODO lo crudo, cambia a: datos_para_ragas = todos_datos[:800]
    datos_para_ragas = comentarios_validos[:800]  # límite razonable para no gastar demasiado

    if datos_para_ragas:
        ragas_samples = []
        for item in datos_para_ragas:
            texto = item.get("texto") or item.get("contenido") or item.get("text") or ""
            if len(texto.strip()) > 30:
                ragas_samples.append({
                    "text": texto,
                    "source": item.get("plataforma", "unknown"),
                    "url": item.get("url") or item.get("video_url") or "N/A",
                    "date": item.get("date") or item.get("fecha") or "N/A"
                })

        ragas_output = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_original_scraped": len(todos_datos),
            "total_after_filter": len(comentarios_validos),
            "sample_for_ragas": ragas_samples
        }

        ragas_file = f"ragas_ready_sample_{timestamp}.json"
        with open(ragas_file, "w", encoding="utf-8") as f:
            json.dump(ragas_output, f, ensure_ascii=False, indent=2)

        print(f"   → Archivo para Ragas creado: {ragas_file}")
        print(f"      Contiene {len(ragas_samples)} comentarios listos para generación sintética.")
    else:
        print("   No hay suficientes comentarios válidos para preparar Ragas aún.")
        
        # ───────────────────────────────────────────────────────────────
    #   (Opcional) Generar testset sintético con Ragas ahora mismo
    # ───────────────────────────────────────────────────────────────

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.documents import Document
        print("\n🧪 Generando testset sintético con Ragas (puede tardar)...")

        # Convertir a LangChain Documents
        lc_docs = [
            Document(
                page_content=item["text"],
                metadata={"source": item["source"], "url": item["url"]}
            )
            for item in ragas_samples[:100]  # límite para no gastar mucho
        ]

        generator = TestsetGenerator.from_langchain(
            generator_llm=ChatOpenAI(model="gpt-4o-mini"),
            critic_llm=ChatOpenAI(model="gpt-4o-mini"),
            embeddings=OpenAIEmbeddings()
        )

        testset = generator.generate_with_langchain_docs(
            lc_docs,
            testset_size=10,  # 30-50 es buen comienzo
        )

        testset.to_pandas().to_csv(f"ragas_testset_{timestamp}.csv", index=False)
        print(f"   → Testset generado y guardado: ragas_testset_{timestamp}.csv")

    except ImportError:
        print("   Ragas o dependencias no instaladas → omite generación automática.")
    except Exception as e:
        print(f"   Error al generar testset con Ragas: {e}")
            
        
        
    total = stats_globales["opinion"] + stats_globales["informativo"]

    if total > 0:
        stats_globales["opinion_pct"] = round(stats_globales["opinion"] * 100 / total)
        stats_globales["informativo_pct"] = round(stats_globales["informativo"] * 100 / total)
    else:
        stats_globales["opinion_pct"] = 0
        stats_globales["informativo_pct"] = 0
    

    print("📊 Agregando comentarios válidos al RAG...")
    rag.agregar_comentarios(comentarios_validos)
    print(f"✅ Comentarios válidos procesados: {len(comentarios_validos)}")
        
        # VERIFICACIÓN CRÍTICA:
    print(f"\n🔍 VERIFICACIÓN RAG:")
    print(f"   - Comentarios procesados: {len(comentarios_validos)}")
    print(f"   - Documentos en RAG: {rag.get_total_documents()}")
    print(f"   - Guardado en: {rag.persist_directory}")
        
        # Forzar guardado explícito
    if hasattr(rag, 'guardar'):
        print("\n💾 Guardando RAG en disco...")
        rag.guardar()
     # Verificar físicamente si existe
    import os
    if os.path.exists(rag.persist_directory):
        files = os.listdir(rag.persist_directory)
        print(f"   - Archivos en directorio: {len(files)} archivos")
        for f in files[:5]:
            size = os.path.getsize(os.path.join(rag.persist_directory, f))
            print(f"     • {f} ({size:,} bytes)")
    else:
        print(f"   ❌ Directorio no existe: {rag.persist_directory}")
    # Verificar persistencia creando nueva instancia
    print("\n🧪 Probando persistencia...")
   
    rag_test = RAGManager(persist_directory=rag.persist_directory)
    print(f"   Documentos en nueva instancia: {rag_test.get_total_documents()}")


        # === NUEVO: Estadísticas de sentiment y gráficos ===
    print("\n📊 Calculando estadísticas de sentiment y generando gráficos...")
    stats = rag.get_sentiment_stats()  # ← Usa el nuevo método de rag_manager
    print(f"Sentiment global: Positivo {stats['positivo']}%, Negativo {stats['negativo']}%, Neutral {stats['neutral']}%")

    # Generar pie chart
    generar_pie_sentiment(stats, filename="sentiment_pie_apple.png")

    # Generar wordcloud (opcional, pero recomendado)
    docs_relevantes = rag.buscar_relevantes(
    "Apple iPhone Mac iOS servicios ecosistema",
    k=120
    )


    textos = [doc.page_content for doc in docs_relevantes]

    generar_wordcloud(textos, filename="wordcloud_apple.png")

    print("✅ Gráficos generados: sentiment_pie_apple.png y wordcloud_apple.png")
    # ==================================================
    
    
    print("\n🧠 FASE 2: Análisis con Ollama + RAG")
    print("=" * 40)
    print(f"📄 Documentos enviados a Ollama: {len(docs_relevantes)}")
    query_reporte = (
    "experiencia uso Apple ecosistema opinion problema me gusta no me gusta "
    "iPhone Mac iOS macOS iCloud AirPods Apple Watch Vision Pro"
)


    reporte = analizar_con_ollama(
        rag,
        stats=stats,
        query=query_reporte,
        modo="reporte"
    )


    total = len(todos_datos)
    opiniones = sum(1 for c in todos_datos if c.get("tipo") == "opinion")
    informativos = total - opiniones


    if total == 0:
        print("⚠️ No hay opiniones reales suficientes para métricas")
    else:
        opiniones = sum(
            1 for c in comentarios_validos 
            if c["tipo"] in ["opinion", "opinion_negativa"]
        )
        informativos = total - opiniones

        print(f"""
        📊 MÉTRICAS DE FUENTES
        Opinión real: {opiniones} ({opiniones*100//total}%)
        Informativo: {informativos} ({informativos*100//total}%)
        """)



    if isinstance(reporte, dict):

        print("\n📊 RESUMEN DEL REPORTE")
        print("=" * 60)
        if 'error' in reporte:
            print("⚠️ Error en generación: ", reporte['error'])
            if 'texto_crudo' in reporte:
                print("\nTexto crudo generado por el modelo (primeros 2000 chars):")
                print(reporte['texto_crudo'][:2000])
        else:
            print(f"Fecha: {reporte.get('fecha_analisis', 'N/A')}")
            print(f"Comentarios analizados: {reporte.get('total_comentarios_analizados', 'N/A')}")
            print(f"\nPercepción general:\n{reporte.get('percepcion_general', 'No disponible')}")
            sentimiento = reporte.get('sentimiento_general', {})
            print(f"\nSentimiento: Positivo {sentimiento.get('positivo', 0)}% | Negativo {sentimiento.get('negativo', 0)}% | Neutral {sentimiento.get('neutral', 0)}%")
            print(f"\nFortalezas: {', '.join(reporte.get('fortalezas', [])[:5])}")
            print(f"Debilidades: {', '.join(reporte.get('debilidades', [])[:5])}")
            print(f"\nResumen ejecutivo:\n{reporte.get('resumen_ejecutivo', 'No disponible')}")
    else:
        print("\n⚠️ No se generó reporte.")

    
    print("\n" + "="*60)
    print("💬 MODO INTERACTIVO (CON MEMORIA de conversación)")
    print("="*60)
    print("Puedes preguntar sobre percepción de marca. Ejemplos:")
    print("  - ¿Qué opinan del iPhone 16?")
    print("  - ¿Ha mejorado la percepción de la batería?")
    print("  - porcentaje de sentimiento positivo")
    print("Escribe 'salir' para terminar\n")

    while True:
        pregunta = input("\n🤔 Tu pregunta: ").strip()
        
        if pregunta.lower() in ['salir', 'exit', 'quit', 'q']:
            print("\n👋 ¡Hasta luego! La memoria de esta sesión se perderá al cerrar.")
            break
        
        if not pregunta:
            print("⚠️ Escribe una pregunta válida.")
            continue
        
        pregunta_lower = pregunta.lower()
        
        # 1. Preguntas cuantitativas → responden con stats precalculadas (sin LLM)
        if any(p in pregunta_lower for p in [
            "porcentaje", "porcentajes", "cuántos", "cuantas", "cantidad",
            "distribución", "proporción", "%", "cuánto", "cuánta"
        ]):
            print("\n📊 Respondiendo con estadísticas calculadas...")
            responder_con_stats(stats_globales, fuentes_stats)
            continue
        
        # 2. Preguntas sobre ruido / pipeline (debug)
        elif any(p in pregunta_lower for p in ["ruido", "descartados", "filtrado", "filtro"]):
            print(f"""
            📉 Métricas del pipeline de limpieza:
            • Comentarios descartados por ruido:      {stats_pipeline.get("descartados_ruido", 0)}
            • Comentarios demasiado cortos:           {stats_pipeline.get("descartados_cortos", 0)}
            • Total scrapeados inicialmente:          {stats_pipeline.get("total_scrapeados", 0)}
            • Comentarios válidos después de filtros: {stats_pipeline.get("validos", 0)}
            """)
            continue
        
        # 3. Todo lo demás → va a la IA con RAG + memoria
        print("\n🤖 Analizando con RAG + memoria + Ollama...", end="", flush=True)
        
        # Recuperamos contexto relevante (k más bajo = más rápido)
        docs = rag.buscar_relevantes(pregunta, k=70)   # 30-40 es un buen balance ahora
        
        if not docs:
            context_text = "No se recuperaron comentarios relevantes para esta pregunta."
        else:
            context_text = "\n\n".join([
                f"[{i+1}] {doc.page_content[:450]}... "
                f"(plataforma: {doc.metadata.get('plataforma', 'n/a')}, "
                f"fecha: {doc.metadata.get('fecha', 'n/a')})"
                for i, doc in enumerate(docs)
            ])
        
        try:
            respuesta = chain.invoke({
                "question": pregunta,
                "context": context_text
            })
            
            print("\r✅ Respuesta generada:")
            print(respuesta.strip())
            print("-"*80)
            
            # Guardar en memoria
            memory.save_context(
                {"input": pregunta},
                {"output": respuesta}
            )
            
        except Exception as e:
            print("\r❌ Error al generar respuesta:")
            print(str(e))
            print("Posibles causas: Ollama no está corriendo, prompt mal configurado o memoria saturada.")
            continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'scraper' in locals() and hasattr(scraper, 'cerrar_selenium'):
            scraper.cerrar_selenium()
     