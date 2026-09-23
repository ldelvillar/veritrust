"""Worker de arq que ejecuta el pipeline multiagente fuera del request HTTP."""

import asyncio
import logging

from arq import cron, func, run_worker
from arq.connections import RedisSettings
from arq.constants import job_key_prefix

from app.agents.errors import (
    OllamaConnectionError,
    ainvoke_graph,
)
from app.agents.main import (
    PIPELINE_STAGES,
    create_evidence_graph,
    create_graph,
    describe_pipeline,
)
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
from app.schemas.mcp import EVIDENCE_RESULT_TTL_SECONDS, MAX_ABSTRACT_CHARS
from app.utils.email import (
    send_analysis_failed_email,
    send_analysis_no_claims_email,
    send_analysis_ready_email,
)
from app.utils.extract_text_from_file import FileExtractionError, extract_text_from_file
from app.utils.extract_text_from_url import URLExtractionError, extract_text_from_url
from app.utils.llm import ensure_llm_available

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
        # Persistir el texto para que la búsqueda del historial funcione aunque el pipeline falle.
        await set_analysis_input_text(analysis_id=analysis_id, input_text=text)

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

        # Cobertura 1.0 sin fuentes significa caída total.
        evidence_coverage = result.get("evidence_coverage")
        if evidence_coverage == 1.0 and not sources:
            evidence_coverage = None

        if not label:
            await fail_analysis(
                analysis_id=analysis_id, error_code=ErrorCode.NO_MEDICAL_CLAIMS.value
            )
            await send_analysis_no_claims_email(
                to=recipient_email, analysis_id=analysis_id
            )
            return

        if not explanation:
            logger.warning("[Worker] Análisis %s sin informe del experto", analysis_id)

        await complete_analysis(
            analysis_id=analysis_id,
            label=str(label),
            confidence=confidence,
            explanation=explanation,
            claims=result.get("claims") or [],
            sources=sources,
            evidence_coverage=evidence_coverage,
            pipeline=ctx["pipeline"],
        )
        logger.info("[Worker] Análisis %s completado (%s)", analysis_id, label)
        completed_ok = True
    except OllamaConnectionError:
        logger.exception("[Worker] No se pudo conectar a Ollama para %s", analysis_id)
        await _fail_and_notify(ErrorCode.CONNECTION.value)
    except Exception:
        logger.exception("[Worker] Error inesperado analizando %s", analysis_id)
        await _fail_and_notify(ErrorCode.INTERNAL.value)

    if completed_ok:
        await send_analysis_ready_email(to=recipient_email, analysis_id=analysis_id)


def _truncate_abstract(text: str | None) -> str | None:
    """Recorta el resumen para acotar el tamaño del resultado guardado en Redis."""
    if not text or len(text) <= MAX_ABSTRACT_CHARS:
        return text
    return text[:MAX_ABSTRACT_CHARS].rstrip() + "…"


async def run_evidence_search(ctx: dict, claim: str) -> dict:
    """
    Busca y juzga la evidencia de una afirmación sin
    emitir veredicto; devuelve un dict serializable.
    """
    logger.info("[Worker] Procesando búsqueda de evidencia")
    initial_state: dict[str, object] = {
        "input_text": neutralize_delimiters(claim),
        "extracted_statements": [],
        "translated_statements": [],
        "claim_evidence": [],
        "valid_claims": 0,
    }

    try:
        result = await asyncio.wait_for(
            ainvoke_graph(ctx["evidence_system"], initial_state),
            timeout=get_settings().analysis_job_timeout_seconds,
        )
    except TimeoutError:
        logger.warning("[Worker] La búsqueda de evidencia agotó el tiempo")
        return {"error_code": ErrorCode.SERVICE_UNAVAILABLE.value}
    except OllamaConnectionError:
        logger.exception("[Worker] No se pudo conectar al LLM en la búsqueda")
        return {"error_code": ErrorCode.CONNECTION.value}
    except Exception:
        logger.exception("[Worker] Error inesperado en la búsqueda de evidencia")
        return {"error_code": ErrorCode.INTERNAL.value}

    claims = result.get("claim_evidence") or []
    if not claims:
        return {"error_code": ErrorCode.NO_MEDICAL_CLAIMS.value}

    for entry in claims:
        for hit in entry.get("hits") or []:
            hit["abstract"] = _truncate_abstract(hit.get("abstract"))

    return {
        "claims": claims,
        "unsearched_claims": max(0, int(result.get("valid_claims") or 0) - len(claims)),
    }


async def reap_stale_analyses(ctx: dict) -> None:
    """Cron: marca como ``failed`` los análisis ``pending`` huérfanos."""
    threshold = get_settings().analysis_stale_after_seconds
    stale_ids = await list_stale_pending_analysis_ids(older_than_seconds=threshold)
    if not stale_ids:
        return

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
    get_settings().validate_runtime(require_cors=False, require_mcp=False)
    ensure_llm_available()
    prompts = load_prompts()
    ctx["verification_system"] = create_graph(prompts)
    ctx["pipeline"] = describe_pipeline(prompts)
    ctx["evidence_system"] = create_evidence_graph(prompts)
    await get_pool()
    logger.info("[Worker] Listo para procesar análisis")


async def shutdown() -> None:
    """Cierra el pool de base de datos al parar el worker."""
    await close_pool()


class WorkerSettings:
    """Configuración del worker de arq."""

    functions = [
        run_analysis,
        # El resultado se guarda para que get_evidence lo recoja aunque la llamada MCP ya expirase.
        func(run_evidence_search, keep_result=EVIDENCE_RESULT_TTL_SECONDS),
    ]
    cron_jobs = [cron(reap_stale_analyses, second=0)]  # ~una vez por minuto
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = (
        get_settings().analysis_job_timeout_seconds + _JOB_TIMEOUT_GRACE_SECONDS
    )
    max_jobs = get_settings().worker_max_jobs
    keep_result = 0
    health_check_interval = 30


def main() -> None:
    """Entrypoint del worker (``python -m app.worker``)."""
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    run_worker(WorkerSettings, redis_settings=redis_settings)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
