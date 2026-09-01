"""Endpoint público que publica los límites de entrada que aplica la API."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH, MIN_INPUT_TEXT_LENGTH
from app.schemas.config import ClientConfig
from app.utils.extract_text_from_file import ALLOWED_FILE_SUFFIXES

router = APIRouter()


@router.get("", response_model=ClientConfig)
async def get_client_config() -> ClientConfig:
    """Devuelve los límites que aplica la API para que el cliente no los duplique."""
    return ClientConfig(
        max_file_bytes=get_settings().max_file_bytes,
        allowed_file_suffixes=sorted(ALLOWED_FILE_SUFFIXES),
        min_input_text_length=MIN_INPUT_TEXT_LENGTH,
        max_input_text_length=MAX_INPUT_TEXT_LENGTH,
    )
