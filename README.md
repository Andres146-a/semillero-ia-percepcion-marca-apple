# Agente IA - Análisis de Percepción de Marca (Apple)

**Semillero IA - Proyecto Final 2026**  
**Tema asignado**: Agente que analiza percepción de marca mediante web scraping de comentarios e interacciones en redes sociales y foros.

**Integrantes**  
- Matyas Cañola Salazar (@Andres146-a)
- José Jeremy Samaniego Lago
- Cerezo Indio Cristian Ariel
- Piza Lema Ricardo Arturo

**Video de presentación**  
[Ver demo en YouTube / Google Drive]  


**Repositorio**: https://github.com/Andres146-a/semillero-ia-percepcion-marca-apple

## Descripción del proyecto

Este agente IA recolecta comentarios reales de usuarios en YouTube, Reddit, foros (MacRumors) y otras fuentes para analizar la percepción de la marca **Apple**. Utiliza técnicas de web scraping, deduplicación avanzada, RAG (Retrieval-Augmented Generation) y un LLM local (Llama 3.1 8B vía Ollama) para generar reportes automáticos con:

- Percepción general  
- Sentimiento (positivo/negativo/neutral)  
- Fortalezas y debilidades  
- Problemas frecuentes  
- Tendencias emergentes  
- Resumen ejecutivo  

Además incluye un modo interactivo donde puedes preguntar en tiempo real (ej. "¿Qué opinan del precio de iPhone?", "¿Por qué algunos cambian a Android?").

**Objetivo principal**  
Detectar tempranamente quejas, tendencias y oportunidades de mejora en la percepción de marca, todo con tecnología local y ética (sin compartir citas literales por privacidad).

## Casos de uso principales

1. **Monitoreo continuo**  
   Analista de marketing obtiene reportes semanales automáticos para detectar problemas antes de que se vuelvan virales.

2. **Análisis post-lanzamiento**  
   Equipo de producto entiende reacción inmediata a nuevos dispositivos (ej. iPhone 16, iOS 18) en minutos.

3. **Comparación competitiva**  
   Estrategas comparan percepción de Apple vs Samsung/Android/Google para ajustar campañas.

4. **Demo interactivo**  
   Presentaciones en vivo: scraping rápido + preguntas en tiempo real + reporte PDF.

## Diagramas
<img width="8192" height="6682" alt="Apple Sentiment RAG Flow-2026-01-23-212701" src="https://github.com/user-attachments/assets/e5c1e9c0-2b18-4f1d-9673-948762d3cc7c" />

<img width="8192" height="2443" alt="Start Decision Options Flow-2026-01-23-212715" src="https://github.com/user-attachments/assets/5e9152d2-8b36-4ed5-9cc7-fafae5165818" />
<img width="2614" height="5305" alt="Calificación en SIUG Flow-2026-01-23-212729" src="https://github.com/user-attachments/assets/ebe08009-6fdf-45cc-843f-38abcc100d88" />

<img width="2614" height="5305" alt="Calificación en SIUG Flow-2026-01-23-212738" src="https://github.com/user-attachments/assets/e643372a-7885-42a1-be2c-84724851d4dd" />


## Tecnologías utilizadas

- **Lenguaje**: Python 3.11  
- **Scraping**:  
  - YouTube: yt-dlp / API no oficial  
  - Reddit: PRAW  
- **Procesamiento**: rapidfuzz (dedup fuzzy), sentence-transformers (reranking CrossEncoder)  
- **RAG**: LangChain + Chroma (vector store) + HuggingFace Embeddings (all-MiniLM-L6-v2)  
- **LLM**: Ollama (Llama 3.1 8B local)  
- **Memoria**: LangChain ConversationSummaryBufferMemory  
- **Visualización**: Matplotlib (pie chart + wordcloud)  
- **Opcional**: reportlab (PDF), Tkinter (GUI básica)

## Instalación y ejecución

### Requisitos

1. Python 3.11+  
2. Ollama instalado y modelo descargado de manera local:
   ```bash
   ollama pull llama3.1:8b
   ```
   2.1 Solo si no tiene el ollama corriendo: 
      ```md   
      ollama serve
      ```

## Cómo correr

### 1. Clonar repositorio:
  ```md
git clone https://github.com/Andres146-a/semillero-ia-percepcion-marca-apple.git
```

### 2. Activa entorno virtual (obligatorio)
   ```md

python -m venv venv
```
   ```md  
.\venv\Scripts\activate  # Windows
```
```
source venv/bin/activate  # Linux/Mac
```

### 3. Instala dependencias
```md  
pip install -r requirements_advanced.txt
```
### 4. Corre el agente
```md  
python main_integradov1.py
```
Scrapea datos frescos
Limpia y procesa
Genera reporte JSON + gráficos
Entra en modo interactivo (pregunta lo que quieras)

## Estructura del repositoriosemillero-ia-percepcion-marca-apple/
```text
web-Scraping/
├── config/
│   └── patrones.json
├── detectors/
│   └── detector_tipo.py
├── drivers/
│   └── msedgedriver.exe
├── models/
│   ├── datos_comunes.py
│   └── __init__.py
├── processors/
│   └── normalizador.py
├── rag/
│   └── rag_manager.py
├── scrapers/
│   ├── base.py
│   ├── scraper_heuristicas.py
│   ├── scraper_hibrido.py
│   ├── scraper_patrones.py
│   ├── scraper_reddit.py
│   ├── scraper_selenium.py
│   ├── scraper_youtubeV2.py
│   └── scraper_youtubeV2v2.py
├── utils/
│   ├── downloader.py
│   └── visualizacion.py
├── main_integradov1.py
├── README.md
└── requirements_advanced.txt
```
## Cómo funciona (resumen técnico)

Scraping → Recolecta comentarios reales de múltiples fuentes con retrasos para evitar bloqueos.
Limpieza → Elimina duplicados (exactos, fuzzy con rapidfuzz, semánticos con cosine) y filtra solo opiniones reales.
RAG → Indexa en Chroma con embeddings MiniLM → retrieval rápido + reranking con CrossEncoder.
Análisis → Ollama genera reporte JSON estructurado y responde preguntas interactivas con memoria.
Salidas → Reporte JSON/PDF + gráficos + interacción en consola (próximo: Tkinter).


## Limitaciones y mejoras futuras

X/Twitter aún sin datos (problemas de cuentas)
Sentiment básico (VADER) → futuro: modelo multilingüe
Interfaz consola → futuro: Tkinter o web (Streamlit/Gradio)
Volumen: hasta ~10k comentarios por ejecución (escalable con más hardware)

Muchas gracias por revisar...Si el proyecto es seleccionado, me encantaria poder explicar lo poco que se más a detalle y aprender mucho más en las pasantías de Netlife. 

Correo: matiascanolas@ug.edu.ec
