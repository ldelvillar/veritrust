"""Unit tests for the Langfuse tracing setup (app.core.tracing)."""

from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from app.core.tracing import _redact


def test_a_masked_span_carries_no_submitted_text(monkeypatch):
    monkeypatch.delenv("LANGFUSE_TRACING_ENABLED")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    client = Langfuse(
        public_key="pk-lf-dummy",
        secret_key="sk-lf-dummy",
        base_url="http://127.0.0.1:9",
        tracer_provider=provider,
        mask=_redact,
        should_export_span=lambda span: False,
    )

    with client.start_as_current_observation(
        name="pipeline",
        input={"input_text": "Tengo diabetes y tomo metformina"},
        output={"medical_explanation": "La metformina reduce la glucosa"},
    ):
        pass
    client.shutdown()

    (span,) = exporter.get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["langfuse.observation.input"] == "<redacted>"
    assert "metformina" not in str(dict(span.attributes))
