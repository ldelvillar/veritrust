"""Este módulo define el esquema de los límites de entrada que la API publica."""

from typing import List

from pydantic import BaseModel


class ClientConfig(BaseModel):
    """Límites de entrada que aplica la API, para que el cliente valide antes de enviar."""

    max_file_bytes: int
    allowed_file_suffixes: List[str]
    min_input_text_length: int
    max_input_text_length: int
