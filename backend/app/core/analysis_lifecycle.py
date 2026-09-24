"""Ciclo de vida de un análisis: la única vía para abrirlo, encolarlo y reabrirlo."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from app.db import analysis_transitions as transitions
from app.db.history import get_user_analysis_status
from app.db.pool import DatabaseError
from app.schemas.analysis import AnalysisOrigin, AnalysisRequest, SourceType
from app.schemas.errors import ErrorCode
from app.utils.extract_text_from_file import ALLOWED_FILE_SUFFIXES

logger = logging.getLogger(__name__)

_DEFAULT_FILENAME = "documento"
_MAX_FILENAME_CHARS = 255
_PDF_SIGNATURE = b"%PDF"


class QueueUnavailable(RuntimeError):
    """La cola de análisis no respondió."""


class AnalysisQueue(Protocol):
    """Cola donde espera cada análisis pendiente hasta que un worker lo ejecuta."""

    async def enqueue(self, analysis_id: str, *, notify_email: str | None) -> None:
        """Encola la Run de un análisis pendiente; lanza QueueUnavailable si no puede."""
        ...

    async def is_live(self, analysis_id: str) -> bool:
        """Indica si el análisis tiene un job en cola o en ejecución."""
        ...


class AnalysisRefused(Exception):
    """El ciclo de vida se negó a abrir el análisis; ``code`` es el motivo del contrato."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


# Motivos con los que puede rechazarse una apertura; los adaptadores los traducen a su transporte.
REFUSAL_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.SERVICE_UNAVAILABLE,
        ErrorCode.INVALID_FILE,
        ErrorCode.FILE_TOO_LARGE,
        ErrorCode.ANALYSIS_SAVE_FAILED,
        ErrorCode.ANALYSIS_FETCH_FAILED,
        ErrorCode.ANALYSIS_NOT_FOUND,
        ErrorCode.ANALYSIS_NOT_RETRYABLE,
        ErrorCode.ANALYSIS_RETRY_FAILED,
        ErrorCode.ANALYSIS_NOT_REANALYZABLE,
        ErrorCode.ANALYSIS_REANALYZE_FAILED,
    }
)


@dataclass(frozen=True)
class Submitter:
    """Quién abre el análisis, desde qué Origin y a qué email avisar al terminar."""

    user_id: str
    origin: AnalysisOrigin
    notify_email: str | None = None


class FileUpload(Protocol):
    """Archivo subido para analizar; el ``UploadFile`` de Starlette lo cumple tal cual."""

    @property
    def filename(self) -> str | None:
        """Nombre original del archivo, si el cliente lo envió."""
        ...

    @property
    def size(self) -> int | None:
        """Tamaño declarado en bytes, si se conoce antes de leerlo."""
        ...

    async def read(self) -> bytes:
        """Lee el contenido completo del archivo."""
        ...


class AnalysisIntake:
    """Abre análisis ``pending`` (altas, Retry y Reanalyze) y los deja encolados."""

    def __init__(self, queue: AnalysisQueue | None, *, max_file_bytes: int) -> None:
        self._queue = queue
        self._max_file_bytes = max_file_bytes

    async def submit(self, submitter: Submitter, request: AnalysisRequest) -> str:
        """Da de alta un análisis de texto o URL y devuelve su id ya encolado."""
        queue = self._require_queue()
        is_url = request.source_type == SourceType.URL
        try:
            analysis_id = await transitions.insert_pending(
                user_id=submitter.user_id,
                origin=submitter.origin,
                source_type=request.source_type.value,
                input_text=None if is_url else request.text,
                input_url=str(request.url) if is_url and request.url else None,
            )
        except DatabaseError as exc:
            logger.exception("No se pudo crear el análisis pendiente")
            raise AnalysisRefused(ErrorCode.ANALYSIS_SAVE_FAILED) from exc

        await self._enqueue(queue, analysis_id, submitter)
        return analysis_id

    async def submit_file(self, submitter: Submitter, upload: FileUpload) -> str:
        """Valida y guarda un archivo (PDF/TXT/MD) y devuelve el id de su análisis encolado."""
        queue = self._require_queue()
        filename = (upload.filename or _DEFAULT_FILENAME)[:_MAX_FILENAME_CHARS]
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_FILE_SUFFIXES:
            raise AnalysisRefused(ErrorCode.INVALID_FILE)

        # Rechaza por tamaño antes de leer todo el cuerpo en memoria cuando es posible.
        if upload.size is not None and upload.size > self._max_file_bytes:
            raise AnalysisRefused(ErrorCode.FILE_TOO_LARGE)

        data = await upload.read()
        if len(data) > self._max_file_bytes:
            raise AnalysisRefused(ErrorCode.FILE_TOO_LARGE)

        # Un PDF debe llevar su firma; los .txt/.md se decodifican en el worker.
        if not data or (suffix == ".pdf" and not data.startswith(_PDF_SIGNATURE)):
            raise AnalysisRefused(ErrorCode.INVALID_FILE)

        try:
            analysis_id = await transitions.insert_pending_file(
                user_id=submitter.user_id,
                origin=submitter.origin,
                filename=filename,
                data=data,
            )
        except DatabaseError as exc:
            logger.exception("No se pudo crear el análisis de archivo pendiente")
            raise AnalysisRefused(ErrorCode.ANALYSIS_SAVE_FAILED) from exc

        await self._enqueue(queue, analysis_id, submitter)
        return analysis_id

    async def retry(self, submitter: Submitter, analysis_id: str) -> str:
        """Devuelve a ``pending`` un análisis ``failed`` propio y lo reencola con su entrada."""
        return await self._reopen(
            submitter,
            analysis_id,
            from_status="failed",
            not_allowed=ErrorCode.ANALYSIS_NOT_RETRYABLE,
            write_failed=ErrorCode.ANALYSIS_RETRY_FAILED,
        )

    async def reanalyze(self, submitter: Submitter, analysis_id: str) -> str:
        """Devuelve a ``pending`` un análisis ``done`` propio, descartando su veredicto, y lo reencola."""
        return await self._reopen(
            submitter,
            analysis_id,
            from_status="done",
            not_allowed=ErrorCode.ANALYSIS_NOT_REANALYZABLE,
            write_failed=ErrorCode.ANALYSIS_REANALYZE_FAILED,
        )

    async def _reopen(
        self,
        submitter: Submitter,
        analysis_id: str,
        *,
        from_status: Literal["failed", "done"],
        not_allowed: ErrorCode,
        write_failed: ErrorCode,
    ) -> str:
        """Reabre el análisis si sigue en ``from_status`` y su Run anterior ya soltó el job."""
        queue = self._require_queue()
        try:
            current = await get_user_analysis_status(
                user_id=submitter.user_id, analysis_id=analysis_id
            )
        except DatabaseError as exc:
            raise AnalysisRefused(ErrorCode.ANALYSIS_FETCH_FAILED) from exc

        if current is None:
            raise AnalysisRefused(ErrorCode.ANALYSIS_NOT_FOUND)
        if current.status != from_status:
            raise AnalysisRefused(not_allowed)

        # Con la Run anterior aún viva, arq descartaría en silencio el nuevo job.
        if await self._is_live(queue, analysis_id):
            raise AnalysisRefused(not_allowed)

        try:
            reopened = await transitions.reopen(
                user_id=submitter.user_id,
                analysis_id=analysis_id,
                from_status=from_status,
            )
        except DatabaseError as exc:
            raise AnalysisRefused(write_failed) from exc

        if not reopened:
            # Perdió la carrera: el estado cambió entre la lectura y la reapertura.
            raise AnalysisRefused(not_allowed)

        await self._enqueue(queue, analysis_id, submitter)
        return analysis_id

    def _require_queue(self) -> AnalysisQueue:
        """Devuelve la cola o rechaza la apertura si el proceso aún no la tiene."""
        if self._queue is None:
            raise AnalysisRefused(ErrorCode.SERVICE_UNAVAILABLE)
        return self._queue

    @staticmethod
    async def _is_live(queue: AnalysisQueue, analysis_id: str) -> bool:
        """Consulta si el análisis tiene un job vivo, rechazando si la cola no responde."""
        try:
            return await queue.is_live(analysis_id)
        except QueueUnavailable as exc:
            raise AnalysisRefused(ErrorCode.SERVICE_UNAVAILABLE) from exc

    @staticmethod
    async def _enqueue(
        queue: AnalysisQueue, analysis_id: str, submitter: Submitter
    ) -> None:
        """Encola la Run y, si la cola falla, deja la fila en ``failed`` antes de rechazar."""
        try:
            await queue.enqueue(analysis_id, notify_email=submitter.notify_email)
        except QueueUnavailable as exc:
            logger.exception("No se pudo encolar el análisis %s", analysis_id)
            # Sin encolado, la fila pasa a failed para que el cliente deje de sondear.
            try:
                await transitions.fail(
                    analysis_id=analysis_id,
                    error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
                )
            except DatabaseError:
                logger.exception(
                    "No se pudo marcar como failed el análisis %s", analysis_id
                )
            raise AnalysisRefused(ErrorCode.SERVICE_UNAVAILABLE) from exc
