"""Dobles del ciclo de vida de un análisis compartidos por las suites de pruebas."""

from app.core.analysis_lifecycle import AnalysisRefused, QueueUnavailable
from app.schemas.errors import ErrorCode

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"


class InMemoryAnalysisQueue:
    """Cola de análisis en memoria que imita el deduplicado por id de arq."""

    def __init__(self, *, live=(), down=False, fail_enqueue=False):
        self.enqueued: list[tuple[str, str | None]] = []
        self.live: set[str] = set(live)
        self.down = down
        self.fail_enqueue = fail_enqueue

    async def enqueue(self, analysis_id, *, notify_email):
        if self.down or self.fail_enqueue:
            raise QueueUnavailable(analysis_id)
        if analysis_id in self.live:
            return
        self.enqueued.append((analysis_id, notify_email))
        self.live.add(analysis_id)

    async def is_live(self, analysis_id):
        if self.down:
            raise QueueUnavailable(analysis_id)
        return analysis_id in self.live

    def finish(self, analysis_id):
        """Simula que el worker terminó la Run y arq soltó su job."""
        self.live.discard(analysis_id)


class StubIntake:
    """Entrada de análisis de mentira que registra cada apertura y puede rechazarla."""

    def __init__(self, *, analysis_id=ANALYSIS_ID, refuse: ErrorCode | None = None):
        self.calls: list[tuple] = []
        self._analysis_id = analysis_id
        self._refuse = refuse

    def _answer(self, analysis_id=None):
        if self._refuse is not None:
            raise AnalysisRefused(self._refuse)
        return analysis_id or self._analysis_id

    async def submit(self, submitter, request):
        self.calls.append(("submit", submitter, request))
        return self._answer()

    async def submit_file(self, submitter, upload):
        self.calls.append(
            ("submit_file", submitter, upload.filename, await upload.read())
        )
        return self._answer()

    async def retry(self, submitter, analysis_id):
        self.calls.append(("retry", submitter, analysis_id))
        return self._answer(analysis_id)

    async def reanalyze(self, submitter, analysis_id):
        self.calls.append(("reanalyze", submitter, analysis_id))
        return self._answer(analysis_id)
