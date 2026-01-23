# visualizations.py
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

def generar_pie_sentiment(stats, filename="sentiment_pie.png"):
    labels = ['Positivo', 'Negativo', 'Neutral']
    sizes = [stats['positivo'], stats['negativo'], stats['neutral']]
    colors = ['#66bb6a', '#ef5350', '#ffa726']
    
    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title('Distribución de Sentiment en Comentarios')
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfico guardado: {filename}")

def generar_wordcloud(textos, filename="wordcloud.png"):
    if not textos:
        return
    text = " ".join(textos)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title('Palabras más frecuentes en comentarios')
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Wordcloud guardado: {filename}")