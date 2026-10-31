"""Analysis lifecycle doubles shared by the test suites."""

from app.core.analysis_lifecycle import AnalysisRefused, QueueUnavailable
from app.schemas.errors import ErrorCode

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"


class InMemoryAnalysisQueue:
    """In-memory analysis queue that mimics arq's dedupe by id."""

    def __init__(self, *, live=(), down=False, fail_enqueue=False):
        self.enqueued: list[tuple[str, str | None]] = []
        self.cancelled: list[list[str]] = []
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

    async def cancel(self, analysis_ids):
        if self.down:
            raise QueueUnavailable(analysis_ids)
        self.cancelled.append(list(analysis_ids))
        self.live.difference_update(analysis_ids)

    def finish(self, analysis_id):
        """Simulate that the worker finished the Run and arq released its job."""
        self.live.discard(analysis_id)


class StubIntake:
    """Fake analysis intake that records each opening and can refuse it."""

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

    async def cancel_runs(self, analysis_ids):
        self.calls.append(("cancel_runs", list(analysis_ids)))


class RecordingNotifier:
    """Analysis end notice that records each send and can fail on purpose."""

    def __init__(self, *, broken=False):
        self.sent: list[tuple[str, str, ErrorCode | None]] = []
        self._broken = broken

    async def finished(self, *, to, analysis_id, error_code):
        if self._broken:
            raise RuntimeError("proveedor de email caído")
        self.sent.append((to, analysis_id, error_code))


class FakeRun:
    """Fake Run to test the worker's work without a database."""

    def __init__(self, content, analysis_id=ANALYSIS_ID):
        self.analysis_id = analysis_id
        self.content = content
        self.finished_stages: list[str] = []
        self.kept_text: list[str] = []

    async def stage_finished(self, stage):
        self.finished_stages.append(stage)

    async def keep_input_text(self, text):
        self.kept_text.append(text)
