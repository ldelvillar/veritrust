"""Worker de arq que ejecuta el pipeline multiagente fuera del request HTTP.

La ruta ``POST /analysis`` solo inserta una fila ``pending`` y encola un trabajo;
este proceso (arrancado con ``python -m app.worker``) ejecuta la extracción de
URL, el grafo de LangGraph y la inferencia BERT, y actualiza la fila a ``done``
o ``failed``. Al vivir en un proceso aparte respaldado por Redis, un análisis
encolado sobrevive a reinicios del servidor web.
"""

import asyncio
import logging

from arq import cron, run_worker
from arq.connections import RedisSettings

from app.agents.errors import (
    BertInferenceError,
    OllamaConnectionError,
    ainvoke_graph,
)
from app.agents.health_expert import ensure_bert_detector_ready
from app.agents.main import create_graph
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.history import (
    complete_analysis,
    fail_analysis,
    fail_stale_pending_analyses,
)
from app.db.pool import close_pool, get_pool
from app.prompts.agents import load_prompts
from app.schemas.errors import ErrorCode
from app.utils.extract_text_from_url import URLExtractionError, extract_text_from_url
from app.utils.ollama import ensure_ollama_available

configure_logging()
logger = logging.getLogger(__name__)


async def run_analysis(
    ctx: dict,
    analysis_id: str,
    source_type: str,
    text: str | None,
    url: str | None,
) -> None:
    """Ejecuta el pipeline para un análisis pendiente y persiste el resultado."""
    logger.info("[Worker] Procesando análisis %s", analysis_id)

    try:
        if source_type == "url":
            text = await asyncio.to_thread(extract_text_from_url, str(url))
    except URLExtractionError:
        logger.info("[Worker] Extracción de URL fallida para %s", analysis_id)
        await fail_analysis(
            analysis_id=analysis_id, error_code=ErrorCode.URL_EXTRACTION.value
        )
        return

    initial_state: dict[str, object] = {
        "input_text": text,
        "extracted_statements": [],
        "translated_statements": [],
        "sources": [],
        "evidence_coverage": 0.0,
        "label": "",
        "confidence": 0.0,
        "medical_explanation": "",
        "claims": [],
    }

    try:
        result = await ainvoke_graph(ctx["verification_system"], initial_state)

        label = result.get("label") or None
        confidence = result.get("confidence") or None
        explanation = result.get("medical_explanation") or None

        # Sin explicación: el texto no contenía afirmaciones médicas verificables.
        if not explanation:
            await fail_analysis(
                analysis_id=analysis_id, error_code=ErrorCode.NO_MEDICAL_CLAIMS.value
            )
            return

        await complete_analysis(
            analysis_id=analysis_id,
            label=str(label),
            confidence=confidence,
            explanation=str(explanation),
            claims=result.get("claims") or [],
            sources=result.get("sources") or [],
        )
        logger.info("[Worker] Análisis %s completado (%s)", analysis_id, label)
    except OllamaConnectionError:
        logger.exception("[Worker] No se pudo conectar a Ollama para %s", analysis_id)
        await fail_analysis(
            analysis_id=analysis_id, error_code=ErrorCode.CONNECTION.value
        )
    except BertInferenceError:
        logger.exception("[Worker] Fallo del detector BERT para %s", analysis_id)
        await fail_analysis(
            analysis_id=analysis_id, error_code=ErrorCode.INTERNAL.value
        )
    except Exception:
        logger.exception("[Worker] Error inesperado analizando %s", analysis_id)
        await fail_analysis(
            analysis_id=analysis_id, error_code=ErrorCode.INTERNAL.value
        )


async def reap_stale_analyses(ctx: dict) -> None:
    """Cron: marca como ``failed`` los análisis ``pending`` atascados.

    Red de seguridad para filas cuyo worker murió a mitad o cuyo trabajo expiró
    sin actualizar la fila, que de otro modo quedarían ``pending`` para siempre.
    """
    count = await fail_stale_pending_analyses(
        older_than_seconds=get_settings().analysis_stale_after_seconds,
        error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
    )
    if count:
        logger.warning("[Worker] Reaper marcó %d análisis atascados como failed", count)


async def startup(ctx: dict) -> None:
    """Inicializa recursos de IA una vez al arrancar el worker."""
    get_settings().validate_runtime(require_cors=False)
    ensure_ollama_available()
    ensure_bert_detector_ready()
    prompts = load_prompts()
    ctx["verification_system"] = create_graph(prompts)
    await get_pool()
    logger.info("[Worker] Listo para procesar análisis")


async def shutdown() -> None:
    """Cierra el pool de base de datos al parar el worker."""
    await close_pool()


class WorkerSettings:
    """Configuración del worker de arq."""

    functions = [run_analysis]
    cron_jobs = [cron(reap_stale_analyses, second=0)]  # ~una vez por minuto
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = get_settings().analysis_job_timeout_seconds


def main() -> None:
    """Entrypoint del worker (``python -m app.worker``)."""
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    run_worker(WorkerSettings, redis_settings=redis_settings)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
