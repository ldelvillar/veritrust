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
from arq.constants import job_key_prefix

from app.agents.errors import (
    BertInferenceError,
    OllamaConnectionError,
    ainvoke_graph,
)
from app.agents.health_expert import ensure_bert_detector_ready
from app.agents.main import PIPELINE_STAGES, create_graph
from app.agents.sanitize import neutralize_delimiters
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.history import (
    complete_analysis,
    fail_analysis,
    fail_stale_pending_analyses,
    get_file_data_by_id,
    list_stale_pending_analysis_ids,
    set_analysis_input_text,
    set_analysis_stage,
)
from app.db.pool import close_pool, get_pool
from app.prompts.agents import load_prompts
from app.schemas.errors import ErrorCode
from app.utils.email import (
    send_analysis_failed_email,
    send_analysis_no_claims_email,
    send_analysis_ready_email,
)
from app.utils.extract_text_from_file import FileExtractionError, extract_text_from_file
from app.utils.extract_text_from_url import URLExtractionError, extract_text_from_url
from app.utils.ollama import ensure_ollama_available

configure_logging()
logger = logging.getLogger(__name__)

# Etapa previa al grafo (extracción de URL/archivo y preparación del texto).
_PREPARING_STAGE = "preparing"
# Nodo terminado -> siguiente nodo en ejecución, para mostrar la etapa activa.
_NEXT_STAGE = dict(zip(PIPELINE_STAGES, PIPELINE_STAGES[1:]))
# Margen del job_timeout de arq sobre el presupuesto interno; deja notificar antes del corte duro.
_JOB_TIMEOUT_GRACE_SECONDS = 30


async def _set_stage(analysis_id: str, stage: str) -> None:
    """Actualiza la etapa visible del análisis; un fallo aquí nunca debe romper el pipeline."""
    try:
        await set_analysis_stage(analysis_id=analysis_id, stage=stage)
    except Exception:
        logger.warning(
            "[Worker] No se pudo fijar la etapa %s de %s", stage, analysis_id
        )


async def run_analysis(
    ctx: dict,
    analysis_id: str,
    source_type: str,
    text: str | None,
    url: str | None,
    recipient_email: str | None = None,
) -> None:
    """Ejecuta el pipeline para un análisis pendiente y persiste el resultado."""
    logger.info("[Worker] Procesando análisis %s", analysis_id)
    await _set_stage(analysis_id, _PREPARING_STAGE)

    async def _fail_and_notify(error_code: str) -> None:
        await fail_analysis(analysis_id=analysis_id, error_code=error_code)
        await send_analysis_failed_email(to=recipient_email, analysis_id=analysis_id)

    try:
        if source_type == "url":
            text = await asyncio.to_thread(extract_text_from_url, str(url))
    except URLExtractionError:
        logger.info("[Worker] Extracción de URL fallida para %s", analysis_id)
        await _fail_and_notify(ErrorCode.URL_EXTRACTION.value)
        return

    if source_type == "file":
        stored = await get_file_data_by_id(analysis_id=analysis_id)
        if stored is None:
            logger.warning("[Worker] Archivo no encontrado para %s", analysis_id)
            await _fail_and_notify(ErrorCode.FILE_EXTRACTION.value)
            return
        data, filename = stored
        try:
            text = await asyncio.to_thread(extract_text_from_file, data, filename or "")
        except FileExtractionError:
            logger.info("[Worker] Extracción de archivo fallida para %s", analysis_id)
            await _fail_and_notify(ErrorCode.FILE_EXTRACTION.value)
            return
        # Persistimos el texto para que la búsqueda del historial funcione aunque
        # el pipeline falle después.
        await set_analysis_input_text(analysis_id=analysis_id, input_text=text)

    # Neutraliza los marcadores de datos en la entrada antes de que el extractor
    # los interpole, para que el texto del usuario no pueda romper <<USER_INPUT>>.
    if text is not None:
        text = neutralize_delimiters(text)

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

    completed_ok = False
    try:

        async def _advance_stage(completed_node: str) -> None:
            next_stage = _NEXT_STAGE.get(completed_node)
            if next_stage:
                await _set_stage(analysis_id, next_stage)

        await _set_stage(analysis_id, PIPELINE_STAGES[0])
        try:
            result = await asyncio.wait_for(
                ainvoke_graph(
                    ctx["verification_system"], initial_state, on_stage=_advance_stage
                ),
                timeout=get_settings().analysis_job_timeout_seconds,
            )
        except TimeoutError:
            logger.warning("[Worker] El pipeline agotó el tiempo para %s", analysis_id)
            await _fail_and_notify(ErrorCode.SERVICE_UNAVAILABLE.value)
            return

        label = result.get("label") or None
        confidence = result.get("confidence") or None
        explanation = result.get("medical_explanation") or None
        sources = result.get("sources") or []

        # Cobertura 1.0 sin fuentes es el centinela de caída total: no es una medición real.
        evidence_coverage = result.get("evidence_coverage")
        if evidence_coverage == 1.0 and not sources:
            evidence_coverage = None

        # Sin explicación: el texto no contenía afirmaciones médicas verificables.
        if not explanation:
            await fail_analysis(
                analysis_id=analysis_id, error_code=ErrorCode.NO_MEDICAL_CLAIMS.value
            )
            await send_analysis_no_claims_email(
                to=recipient_email, analysis_id=analysis_id
            )
            return

        await complete_analysis(
            analysis_id=analysis_id,
            label=str(label),
            confidence=confidence,
            explanation=str(explanation),
            claims=result.get("claims") or [],
            sources=sources,
            evidence_coverage=evidence_coverage,
        )
        logger.info("[Worker] Análisis %s completado (%s)", analysis_id, label)
        completed_ok = True
    except OllamaConnectionError:
        logger.exception("[Worker] No se pudo conectar a Ollama para %s", analysis_id)
        await _fail_and_notify(ErrorCode.CONNECTION.value)
    except BertInferenceError:
        logger.exception("[Worker] Fallo del detector BERT para %s", analysis_id)
        await _fail_and_notify(ErrorCode.INTERNAL.value)
    except Exception:
        logger.exception("[Worker] Error inesperado analizando %s", analysis_id)
        await _fail_and_notify(ErrorCode.INTERNAL.value)

    if completed_ok:
        await send_analysis_ready_email(to=recipient_email, analysis_id=analysis_id)


async def reap_stale_analyses(ctx: dict) -> None:
    """Cron: marca como ``failed`` los análisis ``pending`` huérfanos."""
    threshold = get_settings().analysis_stale_after_seconds
    stale_ids = await list_stale_pending_analysis_ids(older_than_seconds=threshold)
    if not stale_ids:
        return

    # Las rutas encolan con _job_id=analysis_id, así que la clave del job es derivable.
    redis = ctx["redis"]
    orphan_ids = [
        analysis_id
        for analysis_id in stale_ids
        if not await redis.exists(job_key_prefix + analysis_id)
    ]
    if not orphan_ids:
        return

    count = await fail_stale_pending_analyses(
        analysis_ids=orphan_ids,
        older_than_seconds=threshold,
        error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
    )
    if count:
        logger.warning("[Worker] Reaper marcó %d análisis huérfanos como failed", count)


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
    job_timeout = (
        get_settings().analysis_job_timeout_seconds + _JOB_TIMEOUT_GRACE_SECONDS
    )
    # El pipeline satura CPU/Ollama; concurrencia >1 infla la latencia por job
    max_jobs = get_settings().worker_max_jobs
    # Sin resultados en Redis: una clave arq:result: residual bloquearía el reencolado del retry.
    keep_result = 0
    # Heartbeat en Redis cada 30s (por defecto arq escribe 1/h); lo lee el healthcheck del contenedor.
    health_check_interval = 30


def main() -> None:
    """Entrypoint del worker (``python -m app.worker``)."""
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    run_worker(WorkerSettings, redis_settings=redis_settings)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
