"""Tests del worker de arq: ejecuta el pipeline y traduce errores a estado failed."""

import app.worker as worker
from app.agents.errors import BertInferenceError, OllamaConnectionError
from app.utils.extract_text_from_url import URLExtractionError

ANALYSIS_ID = "11111111-1111-1111-1111-111111111111"


def _patch_db(monkeypatch):
    """Sustituye complete_analysis/fail_analysis por espías que registran llamadas."""
    completed = []
    failed = []

    async def fake_complete(**kwargs):
        completed.append(kwargs)

    async def fake_fail(**kwargs):
        failed.append(kwargs)

    monkeypatch.setattr(worker, "complete_analysis", fake_complete)
    monkeypatch.setattr(worker, "fail_analysis", fake_fail)
    return completed, failed


async def test_run_analysis_completes_on_success(monkeypatch):
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state):
        assert state["input_text"] == "Bleach cures COVID"
        return {
            "label": "falsa",
            "confidence": 0.92,
            "medical_explanation": "No hay evidencia clínica sólida.",
        }

    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "text", "Bleach cures COVID", None)

    assert failed == []
    assert len(completed) == 1
    assert completed[0]["analysis_id"] == ANALYSIS_ID
    assert completed[0]["label"] == "falsa"
    assert completed[0]["confidence"] == 0.92


async def test_run_analysis_forwards_per_claim_verdicts(monkeypatch):
    completed, failed = _patch_db(monkeypatch)

    claims = [
        {"text": "S1", "label": "verdadera", "confidence": 0.88},
        {"text": "S2", "label": "falsa", "confidence": 0.91},
    ]

    async def fake_ainvoke(graph, state):
        return {
            "label": "falsa",
            "confidence": 0.7,
            "medical_explanation": "Informe.",
            "claims": claims,
        }

    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "text", "Texto", None)

    assert failed == []
    assert completed[0]["claims"] == claims


async def test_run_analysis_fails_with_no_medical_claims_on_empty_explanation(
    monkeypatch,
):
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state):
        return {"label": "verdadera", "confidence": 0.6, "medical_explanation": ""}

    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "text", "Texto sin claim", None)

    assert completed == []
    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "NO_MEDICAL_CLAIMS"}]


async def test_run_analysis_extracts_url_text_before_pipeline(monkeypatch):
    completed, failed = _patch_db(monkeypatch)

    def fake_extract(url):
        assert url == "https://ejemplo.com/noticia"
        return "Texto extraído de la URL"

    async def fake_ainvoke(graph, state):
        assert state["input_text"] == "Texto extraído de la URL"
        return {
            "label": "verdadera",
            "confidence": 0.85,
            "medical_explanation": "Información correcta.",
        }

    monkeypatch.setattr(worker, "extract_text_from_url", fake_extract)
    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(
        ctx, ANALYSIS_ID, "url", None, "https://ejemplo.com/noticia"
    )

    assert failed == []
    assert completed[0]["label"] == "verdadera"


async def test_run_analysis_fails_with_url_extraction_error(monkeypatch):
    completed, failed = _patch_db(monkeypatch)

    def fake_extract(url):
        raise URLExtractionError("no se pudo")

    invoked = []

    async def fake_ainvoke(graph, state):
        invoked.append(state)
        return {}

    monkeypatch.setattr(worker, "extract_text_from_url", fake_extract)
    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "url", None, "https://ejemplo.com/x")

    assert completed == []
    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "URL_EXTRACTION"}]
    assert invoked == []  # no se llega a invocar el grafo


async def test_run_analysis_fails_with_connection_on_ollama_error(monkeypatch):
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state):
        raise OllamaConnectionError("connect call failed")

    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "text", "Texto", None)

    assert completed == []
    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "CONNECTION"}]


async def test_run_analysis_fails_with_internal_on_bert_error(monkeypatch):
    """Un fallo del detector BERT acaba en 'failed', no en un veredicto falso."""
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state):
        raise BertInferenceError("modelo no disponible")

    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "text", "Texto", None)

    assert completed == []
    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "INTERNAL"}]


async def test_reap_stale_analyses_fails_pending_rows_past_threshold(monkeypatch):
    calls = []

    async def fake_fail_stale(**kwargs):
        calls.append(kwargs)
        return 3

    monkeypatch.setattr(worker, "fail_stale_pending_analyses", fake_fail_stale)

    await worker.reap_stale_analyses({})

    assert len(calls) == 1
    assert calls[0]["error_code"] == "SERVICE_UNAVAILABLE"
    assert (
        calls[0]["older_than_seconds"]
        == worker.get_settings().analysis_stale_after_seconds
    )


async def test_run_analysis_fails_with_internal_on_unexpected_error(monkeypatch):
    completed, failed = _patch_db(monkeypatch)

    async def fake_ainvoke(graph, state):
        raise RuntimeError("graph exploded")

    monkeypatch.setattr(worker, "ainvoke_graph", fake_ainvoke)

    ctx = {"verification_system": object()}
    await worker.run_analysis(ctx, ANALYSIS_ID, "text", "Texto", None)

    assert completed == []
    assert failed == [{"analysis_id": ANALYSIS_ID, "error_code": "INTERNAL"}]
