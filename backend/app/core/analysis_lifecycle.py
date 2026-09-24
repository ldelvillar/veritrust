"""Ciclo de vida de un análisis: la única vía para abrirlo, ejecutar sus Runs y cerrarlo."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, get_args

from app.db import analysis_transitions as transitions
from app.db.history import get_user_analysis_status
from app.db.pool import DatabaseError
from app.schemas.analysis import (
    AnalysisOrigin,
    AnalysisRequest,
    AnalysisStage,
    SourceType,
)
from app.schemas.errors import ErrorCode
from app.utils.extract_text_from_file import ALLOWED_FILE_SUFFIXES

logger = logging.getLogger(__name__)

_DEFAULT_FILENAME = "documento"
_MAX_FILENAME_CHARS = 255
_PDF_SIGNATURE = b"%PDF"

# Etapas visibles en orden: la preparación de la entrada y luego cada agente del grafo.
_STAGES: tuple[AnalysisStage, ...] = get_args(AnalysisStage)
# Etapa terminada -> siguiente etapa en ejecución.
_NEXT_STAGE: dict[str, AnalysisStage] = dict(zip(_STAGES, _STAGES[1:]))


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


@dataclass(frozen=True)
class TextContent:
    """Texto pegado por el usuario."""

    text: str


@dataclass(frozen=True)
class UrlContent:
    """Página web cuyo texto hay que extraer."""

    url: str


@dataclass(frozen=True)
class FileContent:
    """Archivo subido cuyo texto hay que extraer."""

    data: bytes
    filename: str


AnalysisContent = TextContent | UrlContent | FileContent


@dataclass(frozen=True)
class Completion:
    """Veredicto con el que una Run cierra su análisis como ``done``."""

    label: str
    confidence: float | None
    explanation: str | None
    claims: list[dict]
    sources: list[dict]
    evidence_coverage: float | None
    pipeline: dict


class AnalysisFailure(Exception):
    """La Run termina sin veredicto; ``code`` es el motivo que se guarda en el análisis."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class AnalysisNotifier(Protocol):
    """Aviso al usuario de que su análisis terminó."""

    async def finished(
        self, *, to: str, analysis_id: str, error_code: ErrorCode | None
    ) -> None:
        """Avisa del final; ``error_code`` es None si terminó con veredicto."""
        ...


RunOutcome = Literal["done", "failed", "skipped", "discarded"]


class AnalysisRun:
    """Una Run en curso: su entrada y cómo reporta su avance mientras sigue ``pending``."""

    def __init__(self, analysis_id: str, content: AnalysisContent) -> None:
        self.analysis_id = analysis_id
        self.content = content

    async def stage_finished(self, stage: str) -> None:
        """Muestra la etapa que sigue a ``stage`` (la preparación o un agente) recién terminada."""
        next_stage = _NEXT_STAGE.get(stage)
        if next_stage:
            await self._show(next_stage)

    async def _show(self, stage: AnalysisStage) -> None:
        """Muestra la etapa activa; un fallo aquí nunca rompe la Run."""
        try:
            await transitions.set_stage(analysis_id=self.analysis_id, stage=stage)
        except Exception:
            logger.warning(
                "No se pudo fijar la etapa %s de %s", stage, self.analysis_id
            )

    async def keep_input_text(self, text: str) -> None:
        """Guarda el texto extraído de un archivo para que el historial lo encuentre aunque la Run falle."""
        await transitions.set_input_text(analysis_id=self.analysis_id, input_text=text)


Work = Callable[[AnalysisRun], Awaitable[Completion]]


class AnalysisRunner:
    """Ejecuta las Runs de los análisis pendientes y recoge los análisis huérfanos."""

    def __init__(
        self,
        *,
        queue: AnalysisQueue,
        notifier: AnalysisNotifier,
        run_timeout_seconds: float,
        stale_after_seconds: int,
    ) -> None:
        self._queue = queue
        self._notifier = notifier
        self._run_timeout_seconds = run_timeout_seconds
        self._stale_after_seconds = stale_after_seconds

    async def run(
        self, analysis_id: str, work: Work, *, notify_email: str | None = None
    ) -> RunOutcome:
        """Lleva un análisis ``pending`` a ``done`` o ``failed`` con lo que devuelva ``work``."""
        row = await transitions.load_pending_content(analysis_id)
        if row is None:
            logger.warning("El análisis %s ya no está pendiente", analysis_id)
            return "skipped"

        content = _content_from_row(row)
        if content is None:
            logger.warning("Archivo no encontrado para %s", analysis_id)
            return await self._finish(
                analysis_id, ErrorCode.FILE_EXTRACTION, notify_email
            )

        run = AnalysisRun(analysis_id, content)
        await run._show(_STAGES[0])
        result: Completion | ErrorCode
        try:
            async with asyncio.timeout(self._run_timeout_seconds):
                result = await work(run)
        except AnalysisFailure as exc:
            result = exc.code
        except TimeoutError:
            logger.warning("La Run de %s agotó el tiempo", analysis_id)
            result = ErrorCode.SERVICE_UNAVAILABLE
        except Exception:
            logger.exception("Error inesperado en la Run de %s", analysis_id)
            result = ErrorCode.INTERNAL

        return await self._finish(analysis_id, result, notify_email)

    async def reap_orphans(self) -> int:
        """Pasa a ``failed`` los análisis huérfanos y devuelve cuántos recogió."""
        threshold = self._stale_after_seconds
        stale_ids = await transitions.list_stale_pending_ids(
            older_than_seconds=threshold
        )
        if not stale_ids:
            return 0

        orphan_ids = [
            analysis_id
            for analysis_id in stale_ids
            if not await self._queue.is_live(analysis_id)
        ]
        if not orphan_ids:
            return 0

        count = await transitions.fail_stale(
            analysis_ids=orphan_ids,
            older_than_seconds=threshold,
            error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
        )
        if count:
            logger.warning("Se marcaron %d análisis huérfanos como failed", count)
        return count

    async def _finish(
        self,
        analysis_id: str,
        result: Completion | ErrorCode,
        notify_email: str | None,
    ) -> RunOutcome:
        """Escribe el cierre de la Run si el análisis sigue ``pending`` y avisa al usuario."""
        if isinstance(result, Completion):
            try:
                won = await transitions.complete(
                    analysis_id=analysis_id,
                    label=result.label,
                    confidence=result.confidence,
                    explanation=result.explanation,
                    claims=result.claims,
                    sources=result.sources,
                    evidence_coverage=result.evidence_coverage,
                    pipeline=result.pipeline,
                )
            except DatabaseError:
                logger.exception("No se pudo guardar el veredicto de %s", analysis_id)
                result = ErrorCode.INTERNAL
            else:
                return await self._settle(analysis_id, won, None, notify_email)

        # Un fallo de BD aquí sube a arq: la fila sigue pending y la recoge el reaper.
        won = await transitions.fail(analysis_id=analysis_id, error_code=result.value)
        return await self._settle(analysis_id, won, result, notify_email)

    async def _settle(
        self,
        analysis_id: str,
        won: bool,
        error_code: ErrorCode | None,
        notify_email: str | None,
    ) -> RunOutcome:
        """Avisa solo si el cierre ganó; un cierre tardío sobre otro estado se descarta."""
        if not won:
            logger.warning(
                "El análisis %s ya no estaba pendiente; se descarta su cierre",
                analysis_id,
            )
            return "discarded"

        if notify_email:
            try:
                await self._notifier.finished(
                    to=notify_email, analysis_id=analysis_id, error_code=error_code
                )
            except Exception:
                logger.exception("No se pudo avisar del análisis %s", analysis_id)
        return "done" if error_code is None else "failed"


def _content_from_row(row: dict[str, Any]) -> AnalysisContent | None:
    """Construye la entrada de la Run desde la fila; None si falta el archivo subido."""
    if row["source_type"] == SourceType.URL.value:
        return UrlContent(url=str(row["input_url"]))
    if row["source_type"] == SourceType.FILE.value:
        if row["file_data"] is None:
            return None
        return FileContent(
            data=bytes(row["file_data"]), filename=row["file_filename"] or ""
        )
    return TextContent(text=row["input_text"] or "")
