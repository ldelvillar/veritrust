"""Test de arquitectura: solo el ciclo de vida escribe el estado y la etapa de un análisis (ADR-0001)."""

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


def _writes_state(source: str) -> list[str]:
    """Devuelve las sentencias que dan de alta un análisis o asignan su estado o etapa."""
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


def test_the_check_still_recognises_the_real_transitions():
    # Si los patrones dejaran de reconocer el SQL real, el test anterior pasaría en vacío.
    writes = _writes_state(TRANSITIONS.read_text(encoding="utf-8"))

    assert any("INSERT" in write for write in writes)
    assert any("SET status" in write for write in writes)
    assert any("SET stage" in write for write in writes)
