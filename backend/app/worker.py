"""Worker de arq que ejecuta el pipeline multiagente fuera del request HTTP."""

import asyncio
import logging
from functools import partial

from arq import cron, func, run_worker
from arq.connections import RedisSettings

from app.agents.errors import (
    OllamaConnectionError,
    ainvoke_graph,
)
from app.agents.main import (
    create_evidence_graph,
    create_graph,
    describe_pipeline,
)
from app.agents.sanitize import neutralize_delimiters
from app.core.analysis_jobs import ArqAnalysisQueue
from app.core.analysis_lifecycle import (
    AnalysisFailure,
    AnalysisRun,
    AnalysisRunner,
    Completion,
    FileContent,
    UrlContent,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.pool import close_pool, get_pool
from app.prompts.agents import load_prompts
from app.schemas.errors import ErrorCode
from app.schemas.mcp import EVIDENCE_RESULT_TTL_SECONDS, MAX_ABSTRACT_CHARS
from app.utils.email import ResendNotifier
from app.utils.extract_text_from_file import FileExtractionError, extract_text_from_file
from app.utils.extract_text_from_url import URLExtractionError, extract_text_from_url
from app.utils.llm import ensure_llm_available

configure_logging()
logger = logging.getLogger(__name__)

# Margen del job_timeout de arq sobre el presupuesto interno; deja notificar antes del corte duro.
_JOB_TIMEOUT_GRACE_SECONDS = 30


async def _input_text(run: AnalysisRun) -> str:
    """Obtiene el texto a verificar: el pegado, o el extraído de la URL o del archivo."""
    content = run.content
    if isinstance(content, UrlContent):
        try:
            return await asyncio.to_thread(extract_text_from_url, content.url)
        except URLExtractionError as exc:
            logger.info("[Worker] Extracción de URL fallida para %s", run.analysis_id)
            raise AnalysisFailure(ErrorCode.URL_EXTRACTION) from exc

    if isinstance(content, FileContent):
        try:
            text = await asyncio.to_thread(
                extract_text_from_file, content.data, content.filename
            )
        except FileExtractionError as exc:
            logger.info(
                "[Worker] Extracción de archivo fallida para %s", run.analysis_id
            )
            raise AnalysisFailure(ErrorCode.FILE_EXTRACTION) from exc
        await run.keep_input_text(text)
        return text

    return content.text


async def analyse(ctx: dict, run: AnalysisRun) -> Completion:
    """Convierte la entrada de un análisis pendiente en su veredicto con el grafo multiagente."""
    text = neutralize_delimiters(await _input_text(run))
    initial_state: dict[str, object] = {
        "input_text": text,
        "extracted_statements": [],
        "translated_statements": [],
        "sources": [],
        "medical_explanation": "",
    }

    await run.stage_finished("preparing")
    try:
        result = await ainvoke_graph(
            ctx["verification_system"], initial_state, on_stage=run.stage_finished
        )
    except OllamaConnectionError as exc:
        logger.exception("[Worker] No se pudo conectar al LLM para %s", run.analysis_id)
        raise AnalysisFailure(ErrorCode.CONNECTION) from exc

    verdict = result.get("verdict")
    if verdict is None:
        raise AnalysisFailure(ErrorCode.NO_MEDICAL_CLAIMS)

    explanation = result.get("medical_explanation") or None
    if not explanation:
        logger.warning("[Worker] Análisis %s sin informe del experto", run.analysis_id)

    return Completion(
        verdict=verdict,
        explanation=explanation,
        sources=result.get("sources") or [],
        pipeline=ctx["pipeline"],
    )


async def run_analysis(
    ctx: dict,
    *,
    analysis_id: str,
    notify_email: str | None = None,
) -> None:
    """Ejecuta la Run de un análisis pendiente a través del ciclo de vida."""
    logger.info("[Worker] Procesando análisis %s", analysis_id)
    outcome = await ctx["analysis_runner"].run(
        analysis_id, partial(analyse, ctx), notify_email=notify_email
    )
    logger.info("[Worker] Análisis %s: %s", analysis_id, outcome)


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


async def reap_orphaned_analyses(ctx: dict) -> None:
    """Cron: marca como ``failed`` los análisis huérfanos."""
    await ctx["analysis_runner"].reap_orphans()


async def startup(ctx: dict) -> None:
    """Inicializa recursos de IA una vez al arrancar el worker."""
    settings = get_settings()
    settings.validate_runtime(require_cors=False, require_mcp=False)
    ensure_llm_available()
    prompts = load_prompts()
    ctx["verification_system"] = create_graph(prompts)
    ctx["pipeline"] = describe_pipeline(prompts)
    ctx["evidence_system"] = create_evidence_graph(prompts)
    ctx["analysis_runner"] = AnalysisRunner(
        queue=ArqAnalysisQueue(ctx["redis"]),
        notifier=ResendNotifier(),
        run_timeout_seconds=settings.analysis_job_timeout_seconds,
        stale_after_seconds=settings.analysis_stale_after_seconds,
    )
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
    cron_jobs = [cron(reap_orphaned_analyses, second=0)]  # ~una vez por minuto
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
