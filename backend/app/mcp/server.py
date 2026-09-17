"""Servidor MCP de VeriTrust: verificación de afirmaciones y búsqueda de evidencia."""

import asyncio
import logging
from typing import Annotated, Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field, ValidationError
from redis.exceptions import RedisError
from starlette.applications import Starlette

from app.agents.main import PIPELINE_STAGES
from app.api.dependencies.check_rate_limit import (
    enforce_sliding_window,
    user_rate_limit_key,
)
from app.core.config import get_settings
from app.core.credibility import classify_verdict, compute_credibility
from app.core.errors import make_error_detail
from app.db.history import (
    create_pending_analysis,
    fail_analysis,
    get_user_analysis_by_id,
)
from app.db.pool import DatabaseError
from app.mcp.auth import ClerkOAuthTokenVerifier
from app.schemas.analysis import (
    MAX_INPUT_TEXT_LENGTH,
    MIN_INPUT_TEXT_LENGTH,
    AnalysisRequest,
    SourceType,
)
from app.schemas.errors import ErrorCode
from app.schemas.history import AnalysisHistoryItem
from app.schemas.mcp import (
    MAX_ABSTRACT_CHARS,
    ClaimEvidence,
    EvidenceItem,
    EvidenceSearchResult,
    VerificationResult,
)

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"
# Ruta RFC 9728 de los metadatos del recurso protegido que sirve el SDK para MCP_PATH.
MCP_METADATA_PATH = "/.well-known/oauth-protected-resource/mcp"

_POLL_INTERVAL_SECONDS = 2.0
# Etapas visibles del análisis en orden, para reportar un progreso monótono.
_ANALYSIS_STAGES: tuple[str, ...] = ("preparing", *PIPELINE_STAGES)

_INSTRUCTIONS = (
    "VeriTrust checks medical and health claims against the biomedical literature "
    "(Europe PMC, PubMed, openFDA, and the Spanish medicines agency's CIMA database). "
    "Use verify_claim for a verdict on a text or web page, and search_evidence when you "
    "want the per-claim evidence to reason over yourself. Results are informational, "
    "not medical advice."
)

_VERIFY_DESCRIPTION = (
    "Run VeriTrust's full fact-checking pipeline on a medical text or web page URL: "
    "extract the medical claims, search the literature for each one, and return an "
    "overall label (falsa/incierta/verdadera), confidence, per-claim verdicts, cited "
    "sources, and an expert explanation in Spanish. Pass exactly one of text or url. "
    "The analysis takes minutes and is saved to the user's VeriTrust history; if it "
    "is still running when this call returns, status is 'pending' and you should call "
    "get_verification with the analysis_id."
)

_GET_VERIFICATION_DESCRIPTION = (
    "Get the current state of an analysis started with verify_claim, waiting for it "
    "to finish for a while. Returns the same result shape as verify_claim."
)

_SEARCH_DESCRIPTION = (
    "Return the biomedical evidence for the medical claims in a short text, without a "
    "verdict. Each claim comes with the sources found, each source's abstract "
    "(verbatim third-party text) and VeriTrust's stance assessment (supports, "
    "contradicts, inconclusive). Sources judged unrelated are removed; when judged is "
    "false the judge failed and the sources are unfiltered with no stance."
)


def _tool_error(code: ErrorCode, message: str | None = None) -> ToolError:
    """Construye un error de herramienta con el código y mensaje del contrato de errores."""
    detail = make_error_detail(code, message)
    return ToolError(f"{detail['code']}: {detail['message']}")


def _current_user_id() -> str:
    """Devuelve el usuario de Clerk del token OAuth de la petición en curso."""
    token = get_access_token()
    if token is None or not token.subject:
        raise _tool_error(ErrorCode.UNAUTHENTICATED)
    return token.subject


async def _consume_rate_limit(redis: Any, user_id: str) -> None:
    """Descuenta una llamada del mismo presupuesto por usuario que la API web."""
    settings = get_settings()
    try:
        await enforce_sliding_window(
            redis,
            key=user_rate_limit_key(user_id),
            max_requests=settings.rate_limit_max_requests,
            window=settings.rate_limit_window_seconds,
        )
    except HTTPException as exc:
        detail: dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {}
        raise ToolError(f"{detail.get('code')}: {detail.get('message')}") from exc


def _report_url(analysis_id: str) -> str | None:
    """Enlace al informe completo en la web, con el mismo formato que los emails."""
    base_url = get_settings().app_base_url
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"


def _to_verification(record: AnalysisHistoryItem) -> VerificationResult:
    """Traduce la fila del historial al resultado que ve el cliente MCP."""
    done = record.status == "done"
    status: Literal["pending", "done", "failed"] = (
        "done" if done else "pending" if record.status == "pending" else "failed"
    )
    return VerificationResult(
        status=status,
        analysis_id=record.analysis_id,
        report_url=_report_url(record.analysis_id),
        stage=record.stage if status == "pending" else None,
        label=record.label if done else None,
        verdict=classify_verdict(record.label) if done else None,
        confidence=record.confidence if done else None,
        credibility=compute_credibility(record.label, record.confidence)
        if done
        else None,
        evidence_coverage=record.evidence_coverage if done else None,
        explanation=record.explanation if done else None,
        claims=record.claims or [],
        sources=record.sources or [],
        error_code=record.error_code if status == "failed" else None,
    )


async def _await_analysis(
    ctx: Context, *, user_id: str, analysis_id: str
) -> VerificationResult:
    """Sondea el análisis hasta que termina o se agota la espera, informando del progreso."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + get_settings().mcp_tool_wait_seconds
    last_progress = -1

    while True:
        try:
            record = await get_user_analysis_by_id(
                user_id=user_id, analysis_id=analysis_id
            )
        except DatabaseError as exc:
            raise _tool_error(ErrorCode.ANALYSIS_FETCH_FAILED) from exc
        if record is None:
            raise _tool_error(ErrorCode.ANALYSIS_NOT_FOUND)

        result = _to_verification(record)
        if result.status != "pending":
            return result

        if record.stage in _ANALYSIS_STAGES:
            progress = _ANALYSIS_STAGES.index(record.stage)
            if progress > last_progress:
                last_progress = progress
                await ctx.report_progress(
                    progress, len(_ANALYSIS_STAGES), f"Running: {record.stage}"
                )

        if loop.time() >= deadline:
            result.message = (
                "The analysis is still running. Call get_verification with this "
                "analysis_id to keep waiting for the result."
            )
            return result
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


def _truncate(text: str | None) -> str | None:
    """Recorta el resumen al tope de la respuesta MCP."""
    if not text or len(text) <= MAX_ABSTRACT_CHARS:
        return text
    return text[:MAX_ABSTRACT_CHARS].rstrip() + "…"


def _to_evidence_result(result: dict) -> EvidenceSearchResult:
    """Traduce el resultado del job de evidencia al esquema de la herramienta."""
    claims = []
    for entry in result["claims"]:
        hits = entry.get("hits")
        claims.append(
            ClaimEvidence(
                claim=str(entry.get("original") or entry.get("claim") or ""),
                claim_en=str(entry.get("claim") or ""),
                query=str(entry.get("query") or ""),
                sources_unavailable=hits is None,
                judged=bool(entry.get("judged")),
                evidence=[
                    EvidenceItem(
                        title=hit["title"],
                        url=hit["url"],
                        source=hit.get("source"),
                        year=hit.get("year"),
                        stance=hit.get("stance"),
                        abstract=_truncate(hit.get("abstract")),
                    )
                    for hit in hits or []
                ],
            )
        )
    return EvidenceSearchResult(
        claims=claims, unsearched_claims=int(result.get("unsearched_claims") or 0)
    )


def build_mcp_server(*, arq_pool: Any, redis: Any) -> MCPServer:
    """Construye el servidor MCP con autenticación OAuth de Clerk y sus herramientas."""
    settings = get_settings()
    server = MCPServer(
        "VeriTrust",
        instructions=_INSTRUCTIONS,
        token_verifier=ClerkOAuthTokenVerifier(),
        # Cadenas, no AnyHttpUrl: el SDK conserva el issuer sin la barra final que rompería RFC 8414.
        auth=AuthSettings.model_validate(
            {
                "issuer_url": settings.expected_issuer,
                "resource_server_url": settings.mcp_resource_url,
                # Clerk no liga el token al recurso (RFC 8707); el verificador valida emisor y client_id.
                "validate_token_resource": False,
            }
        ),
    )

    @server.tool(
        description=_VERIFY_DESCRIPTION,
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def verify_claim(
        ctx: Context,
        text: Annotated[
            str | None,
            Field(description="Medical text to fact-check, in any language."),
        ] = None,
        url: Annotated[
            str | None,
            Field(description="Public web page whose text should be fact-checked."),
        ] = None,
    ) -> VerificationResult:
        """Lanza el pipeline completo sobre un texto o una URL y espera su resultado."""
        try:
            request = AnalysisRequest(
                text=text,
                url=url,  # type: ignore[arg-type]
                source_type=SourceType.URL if url is not None else SourceType.TEXT,
            )
        except ValidationError as exc:
            messages = "; ".join(str(error["msg"]) for error in exc.errors())
            raise ToolError(f"Invalid input: {messages}") from exc

        user_id = _current_user_id()
        await _consume_rate_limit(redis, user_id)

        try:
            analysis_id = await create_pending_analysis(
                user_id=user_id, request=request, origin="mcp"
            )
        except DatabaseError as exc:
            logger.exception("[MCP] No se pudo crear el análisis pendiente")
            raise _tool_error(ErrorCode.ANALYSIS_SAVE_FAILED) from exc

        try:
            # Sin email: el cliente MCP recibe el resultado en la propia llamada.
            await arq_pool.enqueue_job(
                "run_analysis",
                analysis_id,
                request.source_type.value,
                request.text,
                str(request.url) if request.url else None,
                None,
                _job_id=analysis_id,
            )
        except (OSError, RedisError) as exc:
            logger.exception("[MCP] No se pudo encolar el análisis %s", analysis_id)
            try:
                await fail_analysis(
                    analysis_id=analysis_id,
                    error_code=ErrorCode.SERVICE_UNAVAILABLE.value,
                )
            except DatabaseError:
                logger.exception(
                    "[MCP] No se pudo marcar como failed el análisis %s", analysis_id
                )
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE) from exc

        return await _await_analysis(ctx, user_id=user_id, analysis_id=analysis_id)

    @server.tool(
        description=_GET_VERIFICATION_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    async def get_verification(
        ctx: Context,
        analysis_id: Annotated[
            str, Field(description="The analysis_id returned by verify_claim.")
        ],
    ) -> VerificationResult:
        """Espera y devuelve el estado de un análisis MCP del usuario."""
        user_id = _current_user_id()
        try:
            UUID(analysis_id)
        except ValueError as exc:
            raise _tool_error(ErrorCode.INVALID_ANALYSIS_ID) from exc
        return await _await_analysis(ctx, user_id=user_id, analysis_id=analysis_id)

    @server.tool(
        description=_SEARCH_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True),
    )
    async def search_evidence(
        ctx: Context,
        claim: Annotated[
            str,
            Field(
                min_length=MIN_INPUT_TEXT_LENGTH,
                max_length=MAX_INPUT_TEXT_LENGTH,
                description="Medical claim or short text, in any language.",
            ),
        ],
    ) -> EvidenceSearchResult:
        """Encola la búsqueda de evidencia en el worker y espera su resultado."""
        user_id = _current_user_id()
        await _consume_rate_limit(redis, user_id)

        try:
            job = await arq_pool.enqueue_job("run_evidence_search", claim.strip())
        except (OSError, RedisError) as exc:
            logger.exception("[MCP] No se pudo encolar la búsqueda de evidencia")
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE) from exc
        if job is None:
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + get_settings().mcp_tool_wait_seconds
        reported_running = False
        await ctx.report_progress(0, 2, "Queued")

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise _tool_error(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    "The evidence search is still queued or running; try again later.",
                )
            try:
                result = await job.result(
                    timeout=min(_POLL_INTERVAL_SECONDS, remaining)
                )
                break
            except TimeoutError:
                if not reported_running and (await job.status()) == "in_progress":
                    reported_running = True
                    await ctx.report_progress(1, 2, "Searching the literature")

        if "error_code" in result:
            raise _tool_error(ErrorCode(result["error_code"]))
        return _to_evidence_result(result)

    return server


def build_mcp_http_app(server: MCPServer) -> Starlette:
    """Devuelve la app Streamable HTTP del servidor, limitada a los hosts configurados."""
    settings = get_settings()
    allowed_hosts = [urlparse(str(settings.mcp_resource_url)).netloc]
    if settings.environment.strip().lower() == "development":
        allowed_hosts += ["localhost:*", "127.0.0.1:*"]
    return server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        # Sin sesión en memoria: cualquier réplica atiende a los clientes de protocolo antiguo.
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=allowed_hosts,
            allowed_origins=settings.cors_origins(),
        ),
    )
