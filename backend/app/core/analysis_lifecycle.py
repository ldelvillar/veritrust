"""Analysis lifecycle, the only way to open an Analysis, run its Runs and close it."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, get_args

from app.core.plans import PlanLimits, history_floor
from app.core.verdict import Verdict
from app.db import analysis_transitions as transitions
from app.db.history import HiddenAnalysis, get_user_analysis_status
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

# Visible stages in order, input preparation first and then each graph agent.
_STAGES: tuple[AnalysisStage, ...] = get_args(AnalysisStage)
# Finished stage to the next running stage.
_NEXT_STAGE: dict[str, AnalysisStage] = dict(zip(_STAGES, _STAGES[1:]))


class QueueUnavailable(RuntimeError):
    """The analysis queue did not respond."""


class AnalysisQueue(Protocol):
    """Queue where each pending Analysis waits until a worker runs it."""

    async def enqueue(self, analysis_id: str, *, notify_email: str | None) -> None:
        """Enqueue the Run of a pending Analysis, raising QueueUnavailable if it cannot."""
        ...

    async def is_live(self, analysis_id: str) -> bool:
        """Tell whether the Analysis has a queued or running job."""
        ...

    async def cancel(self, analysis_ids: Sequence[str]) -> None:
        """Abort the queued or running jobs of the analyses, raising QueueUnavailable if it cannot."""
        ...


class AnalysisRefused(Exception):
    """The lifecycle refused to open the Analysis, with ``code`` as the contract reason."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


# Reasons an opening can be refused with, which the adapters translate to their transport.
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
        ErrorCode.PLAN_REQUIRED,
        ErrorCode.ALLOWANCE_EXHAUSTED,
        ErrorCode.TEXT_TOO_LONG_FOR_PLAN,
    }
)


@dataclass(frozen=True)
class Submitter:
    """Who opens the Analysis, from which Origin, with which Plan and which email to notify when it ends."""

    user_id: str
    origin: AnalysisOrigin
    limits: PlanLimits
    notify_email: str | None = None


class FileUpload(Protocol):
    """Uploaded file to analyse, which Starlette's ``UploadFile`` satisfies as is."""

    @property
    def filename(self) -> str | None:
        """Original file name, if the client sent one."""
        ...

    @property
    def size(self) -> int | None:
        """Declared size in bytes, if known before reading it."""
        ...

    async def read(self) -> bytes:
        """Read the whole file content."""
        ...


class AnalysisIntake:
    """Open ``pending`` analyses (submissions, Retry and Reanalyze), enqueue them and stop the Runs of deleted ones."""

    def __init__(self, queue: AnalysisQueue | None, *, max_file_bytes: int) -> None:
        self._queue = queue
        self._max_file_bytes = max_file_bytes

    async def submit(self, submitter: Submitter, request: AnalysisRequest) -> str:
        """Submit a text or URL Analysis and return its id, already enqueued."""
        queue = self._require_queue()
        is_url = request.source_type == SourceType.URL
        # The schema caps everyone at 10,000 and the Plan can cap lower.
        if not is_url and len(request.text or "") > submitter.limits.max_input_chars:
            raise AnalysisRefused(ErrorCode.TEXT_TOO_LONG_FOR_PLAN)
        try:
            analysis_id = await transitions.insert_pending(
                user_id=submitter.user_id,
                origin=submitter.origin,
                source_type=request.source_type.value,
                input_text=None if is_url else request.text,
                input_url=str(request.url) if is_url and request.url else None,
                limits=submitter.limits,
            )
        except transitions.AllowanceExhausted as exc:
            raise AnalysisRefused(ErrorCode.ALLOWANCE_EXHAUSTED) from exc
        except DatabaseError as exc:
            logger.exception("No se pudo crear el análisis pendiente")
            raise AnalysisRefused(ErrorCode.ANALYSIS_SAVE_FAILED) from exc

        await self._enqueue(queue, analysis_id, submitter)
        return analysis_id

    async def submit_file(self, submitter: Submitter, upload: FileUpload) -> str:
        """Validate and store a file (PDF/TXT/MD) and return the id of its enqueued Analysis."""
        queue = self._require_queue()
        # Refused before reading the body, so a Plan without files does not pay for that memory.
        if not submitter.limits.files:
            raise AnalysisRefused(ErrorCode.PLAN_REQUIRED)
        filename = (upload.filename or _DEFAULT_FILENAME)[:_MAX_FILENAME_CHARS]
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_FILE_SUFFIXES:
            raise AnalysisRefused(ErrorCode.INVALID_FILE)

        # Refuse by size before reading the whole body into memory when possible.
        if upload.size is not None and upload.size > self._max_file_bytes:
            raise AnalysisRefused(ErrorCode.FILE_TOO_LARGE)

        data = await upload.read()
        if len(data) > self._max_file_bytes:
            raise AnalysisRefused(ErrorCode.FILE_TOO_LARGE)

        # A PDF must carry its signature, while .txt and .md are decoded in the worker.
        if not data or (suffix == ".pdf" and not data.startswith(_PDF_SIGNATURE)):
            raise AnalysisRefused(ErrorCode.INVALID_FILE)

        try:
            analysis_id = await transitions.insert_pending_file(
                user_id=submitter.user_id,
                origin=submitter.origin,
                filename=filename,
                data=data,
                limits=submitter.limits,
            )
        except transitions.AllowanceExhausted as exc:
            raise AnalysisRefused(ErrorCode.ALLOWANCE_EXHAUSTED) from exc
        except DatabaseError as exc:
            logger.exception("No se pudo crear el análisis de archivo pendiente")
            raise AnalysisRefused(ErrorCode.ANALYSIS_SAVE_FAILED) from exc

        await self._enqueue(queue, analysis_id, submitter)
        return analysis_id

    async def retry(self, submitter: Submitter, analysis_id: str) -> str:
        """Return an own ``failed`` Analysis to ``pending`` and enqueue it again with its input."""
        return await self._reopen(
            submitter,
            analysis_id,
            from_status="failed",
            not_allowed=ErrorCode.ANALYSIS_NOT_RETRYABLE,
            write_failed=ErrorCode.ANALYSIS_RETRY_FAILED,
        )

    async def reanalyze(self, submitter: Submitter, analysis_id: str) -> str:
        """Return an own ``done`` Analysis to ``pending``, discarding its Verdict, and enqueue it again."""
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
        """Reopen the Analysis if it is still in ``from_status`` and its previous Run has released the job."""
        queue = self._require_queue()
        try:
            current = await get_user_analysis_status(
                user_id=submitter.user_id,
                analysis_id=analysis_id,
                visible_since=history_floor(submitter.limits, datetime.now(UTC)),
            )
        except HiddenAnalysis as exc:
            raise AnalysisRefused(ErrorCode.PLAN_REQUIRED) from exc
        except DatabaseError as exc:
            raise AnalysisRefused(ErrorCode.ANALYSIS_FETCH_FAILED) from exc

        if current is None:
            raise AnalysisRefused(ErrorCode.ANALYSIS_NOT_FOUND)
        if current.status != from_status:
            raise AnalysisRefused(not_allowed)

        # With the previous Run still alive, arq would silently drop the new job.
        if await self._is_live(queue, analysis_id):
            raise AnalysisRefused(not_allowed)

        try:
            # A Retry also needs a free Run, since ending done will consume the first unit.
            reopened = await transitions.reopen(
                user_id=submitter.user_id,
                analysis_id=analysis_id,
                from_status=from_status,
                limits=submitter.limits,
            )
        except transitions.AllowanceExhausted as exc:
            raise AnalysisRefused(ErrorCode.ALLOWANCE_EXHAUSTED) from exc
        except DatabaseError as exc:
            raise AnalysisRefused(write_failed) from exc

        if not reopened:
            # Lost the race because the status changed between the read and the reopening.
            raise AnalysisRefused(not_allowed)

        await self._enqueue(queue, analysis_id, submitter)
        return analysis_id

    async def cancel_runs(self, analysis_ids: Sequence[str]) -> None:
        """Abort the Runs of already deleted analyses, where a queue failure does not undo the deletion."""
        if self._queue is None or not analysis_ids:
            return
        try:
            await self._queue.cancel(analysis_ids)
        except QueueUnavailable:
            # Without an abort, each Run stops at its next stage, or drops its close if it was on the last one.
            logger.warning("No se pudieron abortar las Runs de %s", analysis_ids)

    def _require_queue(self) -> AnalysisQueue:
        """Return the queue, or refuse the opening if the process does not have it yet."""
        if self._queue is None:
            raise AnalysisRefused(ErrorCode.SERVICE_UNAVAILABLE)
        return self._queue

    @staticmethod
    async def _is_live(queue: AnalysisQueue, analysis_id: str) -> bool:
        """Ask whether the Analysis has a live job, refusing if the queue does not respond."""
        try:
            return await queue.is_live(analysis_id)
        except QueueUnavailable as exc:
            raise AnalysisRefused(ErrorCode.SERVICE_UNAVAILABLE) from exc

    @staticmethod
    async def _enqueue(
        queue: AnalysisQueue, analysis_id: str, submitter: Submitter
    ) -> None:
        """Enqueue the Run and, if the queue fails, leave the row ``failed`` before refusing."""
        try:
            await queue.enqueue(analysis_id, notify_email=submitter.notify_email)
        except QueueUnavailable as exc:
            logger.exception("No se pudo encolar el análisis %s", analysis_id)
            # Without an enqueue the row goes failed so the client stops polling.
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
    """Text pasted by the user."""

    text: str


@dataclass(frozen=True)
class UrlContent:
    """Web page whose text must be extracted, up to the cap of the Plan the Analysis was opened with."""

    url: str
    max_chars: int


@dataclass(frozen=True)
class FileContent:
    """Uploaded file whose text must be extracted, up to the cap of the Plan the Analysis was opened with."""

    data: bytes
    filename: str
    max_chars: int


AnalysisContent = TextContent | UrlContent | FileContent


@dataclass(frozen=True)
class Completion:
    """Verdict with which a Run closes its Analysis as ``done``."""

    verdict: Verdict
    explanation: str | None
    sources: list[dict]
    pipeline: dict


class AnalysisFailure(Exception):
    """The Run ends without a Verdict, with ``code`` as the reason stored on the Analysis."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class AnalysisNotifier(Protocol):
    """Notice to the user that their Analysis finished."""

    async def finished(
        self, *, to: str, analysis_id: str, error_code: ErrorCode | None
    ) -> None:
        """Notify the end, with ``error_code`` None when it finished with a Verdict."""
        ...


RunOutcome = Literal["done", "failed", "skipped", "discarded"]


class _AnalysisGone(Exception):
    """The Run's Analysis was deleted or stopped being ``pending`` while it ran."""


class AnalysisRun:
    """A running Run, with its input and how it reports progress while still ``pending``."""

    def __init__(self, analysis_id: str, content: AnalysisContent) -> None:
        self.analysis_id = analysis_id
        self.content = content

    async def stage_finished(self, stage: str) -> None:
        """Show the stage that follows the just finished ``stage`` (preparation or an agent)."""
        next_stage = _NEXT_STAGE.get(stage)
        if next_stage:
            await self._show(next_stage)

    async def _show(self, stage: AnalysisStage) -> None:
        """Show the active stage and stop the Run if its Analysis is no longer pending, never breaking on a DB failure."""
        try:
            shown = await transitions.set_stage(
                analysis_id=self.analysis_id, stage=stage
            )
        except Exception:
            logger.warning(
                "No se pudo fijar la etapa %s de %s", stage, self.analysis_id
            )
            return
        if not shown:
            raise _AnalysisGone(self.analysis_id)

    async def keep_input_text(self, text: str) -> None:
        """Store the text extracted from a file so the History finds it even if the Run fails."""
        await transitions.set_input_text(analysis_id=self.analysis_id, input_text=text)


Work = Callable[[AnalysisRun], Awaitable[Completion]]


class AnalysisRunner:
    """Run the Runs of pending analyses and reap orphaned analyses."""

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
        """Take a ``pending`` Analysis to ``done`` or ``failed`` with whatever ``work`` returns."""
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
        result: Completion | ErrorCode
        try:
            await run._show(_STAGES[0])
            async with asyncio.timeout(self._run_timeout_seconds):
                result = await work(run)
        except _AnalysisGone:
            # Does not rely on arq's abort, which can be delayed or lost if Redis does not respond.
            logger.info(
                "El análisis %s ya no está pendiente; se detiene su Run", analysis_id
            )
            return "discarded"
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
        """Fail the orphaned analyses and return how many were reaped."""
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
        """Write the Run's close if the Analysis is still ``pending`` and notify the user."""
        if isinstance(result, Completion):
            try:
                won = await transitions.complete(
                    analysis_id=analysis_id,
                    verdict=result.verdict,
                    explanation=result.explanation,
                    sources=result.sources,
                    pipeline=result.pipeline,
                )
            except DatabaseError:
                logger.exception("No se pudo guardar el veredicto de %s", analysis_id)
                result = ErrorCode.INTERNAL
            else:
                return await self._settle(analysis_id, won, None, notify_email)

        # A DB failure here bubbles up to arq, leaving the row pending for the reaper.
        won = await transitions.fail(analysis_id=analysis_id, error_code=result.value)
        return await self._settle(analysis_id, won, result, notify_email)

    async def _settle(
        self,
        analysis_id: str,
        won: bool,
        error_code: ErrorCode | None,
        notify_email: str | None,
    ) -> RunOutcome:
        """Notify only if the close won, discarding a late close over another status."""
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
    """Build the Run's input from the row, or None if the uploaded file is missing."""
    if row["source_type"] == SourceType.URL.value:
        return UrlContent(url=str(row["input_url"]), max_chars=row["max_input_chars"])
    if row["source_type"] == SourceType.FILE.value:
        if row["file_data"] is None:
            return None
        return FileContent(
            data=bytes(row["file_data"]),
            filename=row["file_filename"] or "",
            max_chars=row["max_input_chars"],
        )
    return TextContent(text=row["input_text"] or "")
