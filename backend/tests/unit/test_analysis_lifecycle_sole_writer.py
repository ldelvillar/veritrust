"""Architecture test that only the lifecycle writes an Analysis's status and stage (ADR-0001)."""

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
TRANSITIONS = APP / "db" / "analysis_transitions.py"

_INSERT = re.compile(r"INSERT\s+INTO\s+public\.analysis_history\b", re.IGNORECASE)
_UPDATE_SET = re.compile(
    r"UPDATE\s+public\.analysis_history\s+SET\b(.*?)\bWHERE\b",
    re.IGNORECASE | re.DOTALL,
)
_ASSIGNS_STATE = re.compile(r"\b(status|stage)\s*=", re.IGNORECASE)
_WRITES_USAGE = re.compile(
    r"\b(INSERT\s+INTO|UPDATE)\s+public\.usage_events\b", re.IGNORECASE
)


def _writes_state(source: str) -> list[str]:
    """Return the statements that create an Analysis or assign its status or stage."""
    writes = [match.group(0) for match in _INSERT.finditer(source)]
    writes += [
        match.group(0)
        for match in _UPDATE_SET.finditer(source)
        if _ASSIGNS_STATE.search(match.group(1))
    ]
    return writes


def _app_sources() -> dict[str, str]:
    return {
        path.relative_to(APP).as_posix(): path.read_text(encoding="utf-8")
        for path in APP.rglob("*.py")
    }


def test_only_the_lifecycle_imports_the_transitions_sql():
    importers = sorted(
        name
        for name, source in _app_sources().items()
        if "analysis_transitions" in source and name != "db/analysis_transitions.py"
    )

    assert importers == ["core/analysis_lifecycle.py"]


def test_no_other_sql_opens_an_analysis_or_writes_its_status_or_stage():
    offenders = {
        name: writes
        for name, source in _app_sources().items()
        if name != "db/analysis_transitions.py" and (writes := _writes_state(source))
    }

    assert offenders == {}


def test_only_run_completion_and_evidence_searches_write_the_usage_ledger():
    # ADR-0005 has a Run's Usage born with its done and a search's in the worker.
    writers = sorted(
        name for name, source in _app_sources().items() if _WRITES_USAGE.search(source)
    )

    assert writers == ["db/analysis_transitions.py", "db/billing.py"]


def test_the_check_still_recognises_the_real_transitions():
    # If the patterns stopped recognising the real SQL, the previous test would pass vacuously.
    writes = _writes_state(TRANSITIONS.read_text(encoding="utf-8"))

    assert any("INSERT" in write for write in writes)
    assert any("SET status" in write for write in writes)
    assert any("SET stage" in write for write in writes)
