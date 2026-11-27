"""Property tests of the History CSV, whose «Entrada» cell must never open as a formula."""

import csv
import io

from hypothesis import given
from hypothesis import strategies as st

from app.core.history_export import build_history_csv
from app.schemas.history import HistoryExportItem

# Leading characters spreadsheets run as a formula, from OWASP's CSV injection guidance.
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
# Any text, plus text that opens with a trigger, which random text alone rarely does.
_ENTRIES = st.text() | st.builds(
    lambda trigger, rest: trigger + rest, st.sampled_from(_FORMULA_TRIGGERS), st.text()
)
# The field each source type's «Entrada» comes from.
_ENTRY_FIELDS = {"text": "input_text", "url": "input_url", "file": "file_filename"}


def _entry_cell(source_type: str, entry: str) -> str:
    """Return the «Entrada» cell a spreadsheet reads for one exported Analysis."""
    record = HistoryExportItem(
        analysis_id="id",
        source_type=source_type,
        created_at="2026-04-12T09:00:00+00:00",
        **{_ENTRY_FIELDS[source_type]: entry},
    )
    body = build_history_csv([record]).decode("utf-8-sig")
    return list(csv.reader(io.StringIO(body, newline="")))[1][2]


@given(st.sampled_from(sorted(_ENTRY_FIELDS)), _ENTRIES)
def test_an_entry_never_opens_as_a_formula_and_keeps_its_text(
    source_type, entry
) -> None:
    cell = _entry_cell(source_type, entry)

    assert not cell.startswith(_FORMULA_TRIGGERS)
    assert cell in (entry, "'" + entry)
