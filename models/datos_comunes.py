# models/datos_comunes.py
from typing import Optional, Dict, Any

class EsquemaDatos:
    """
    Esquema de datos común para scraping.
    Versión simplificada sin pydantic.
    """
    
    def __init__(
        self,
        id_unico: str,
        titulo: str,
        contenido: str,
        url: str,
        tipo_pagina: str,
        autor: Optional[str] = None,
        fecha: Optional[str] = None,
        categoria_producto: Optional[str] = None,
        sentimiento: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id_unico = id_unico
        self.titulo = titulo
        self.contenido = contenido
        self.autor = autor
        self.fecha = fecha
        self.url = url
        self.tipo_pagina = tipo_pagina
        self.categoria_producto = categoria_producto
        self.sentimiento = sentimiento
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'id_unico': self.id_unico,
            'titulo': self.titulo,
            'contenido': self.contenido,
            'autor': self.autor,
            'fecha': self.fecha,
            'url': self.url,
            'tipo_pagina': self.tipo_pagina,
            'categoria_producto': self.categoria_producto,
            'sentimiento': self.sentimiento,
            'metadata': self.metadata
        }
    
    @classmethod
    def validar(cls, datos: dict) -> bool:
        """Valida los datos mínimos requeridos"""
        campos_requeridos = ['id_unico', 'titulo', 'contenido', 'url', 'tipo_pagina']
        return all(campo in datos for campo in campos_requeridos)