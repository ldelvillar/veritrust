"""VeriTrust MCP server for claim verification and Evidence search."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, TypeVar
from urllib.parse import urlparse
from uuid import UUID, uuid4

from arq.jobs import Job, JobStatus
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
from app.core.analysis_lifecycle import AnalysisIntake, AnalysisRefused, Submitter
from app.core.config import get_settings
from app.core.errors import make_error_detail
from app.core.plans import PlanLimits, limits_for, month_window, remaining
from app.core.rate_limit import (
    RateLimitRefused,
    enforce_sliding_window,
    user_rate_limit_key,
)
from app.db.billing import get_user_subscription, usage_this_month
from app.db.history import get_user_analysis_by_id, get_user_analysis_status
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
    EVIDENCE_RESULT_TTL_SECONDS,
    ClaimEvidence,
    EvidenceItem,
    EvidenceSearchResult,
    VerificationResult,
)

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"
# RFC 9728 path of the protected resource metadata the SDK serves for MCP_PATH.
MCP_METADATA_PATH = "/.well-known/oauth-protected-resource/mcp"

_POLL_INTERVAL_SECONDS = 2.0
# Owner of each Evidence search, so only whoever started it can collect it with get_evidence.
_EVIDENCE_OWNER_KEY = "mcp:evidence_owner:{job_id}"
# Visible Analysis stages in order, to report monotonic progress.
_ANALYSIS_STAGES: tuple[str, ...] = ("preparing", *PIPELINE_STAGES)

_INSTRUCTIONS = (
    "VeriTrust checks medical and health claims against the biomedical literature "
    "(Europe PMC, PubMed, openFDA, and the Spanish medicines agency's CIMA database). "
    "Use verify_claim for a verdict on a text or web page, and search_evidence when you "
    "want the per-claim evidence to reason over yourself. Both run for minutes: when a "
    "result comes back with status 'pending', resume it with get_verification or "
    "get_evidence. Results are informational, not medical advice."
)

_VERIFY_DESCRIPTION = (
    "Run VeriTrust's full fact-checking pipeline on a medical text or web page URL: "
    "extract the medical claims, search the literature for each one, and return an "
    "overall label (falsa/parcialmente falsa/incierta/verdadera), confidence, "
    "per-claim verdicts, cited sources, and an expert explanation in Spanish. "
    "Pass exactly one of text or url. "
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
    "false the judge failed and the sources are unfiltered with no stance. The search "
    "takes minutes; if status is 'pending', call get_evidence with the job_id."
)

_GET_EVIDENCE_DESCRIPTION = (
    "Get the result of a search started with search_evidence, waiting for it to finish "
    "for a while. Returns the same result shape as search_evidence; results are kept "
    "for one hour."
)


def _tool_error(code: ErrorCode, message: str | None = None) -> ToolError:
    """Build a tool error with the error contract's code and message."""
    detail = make_error_detail(code, message)
    return ToolError(f"{detail['code']}: {detail['message']}")


def _current_user_id() -> str:
    """Return the Clerk user of the current request's OAuth token."""
    token = get_access_token()
    if token is None or not token.subject:
        raise _tool_error(ErrorCode.UNAUTHENTICATED)
    return token.subject


async def _pro_caller() -> tuple[str, PlanLimits]:
    """Identify the OAuth token's user and their Plan, read on every call, refusing if it lacks MCP."""
    user_id = _current_user_id()
    try:
        limits = limits_for(await get_user_subscription(user_id))
    except DatabaseError as exc:
        raise _tool_error(ErrorCode.BILLING_FETCH_FAILED) from exc
    if not limits.mcp:
        raise _tool_error(ErrorCode.PLAN_REQUIRED)
    return user_id, limits


async def _require_allowance(user_id: str, limits: PlanLimits) -> None:
    """Refuse an Evidence search when the month's Allowance is used up, not counting searches in progress."""
    start, end = month_window(datetime.now(UTC))
    try:
        usage = await usage_this_month(user_id, start, end)
    except DatabaseError as exc:
        raise _tool_error(ErrorCode.BILLING_FETCH_FAILED) from exc
    if remaining(limits, usage.used, usage.pending) == 0:
        raise _tool_error(ErrorCode.ALLOWANCE_EXHAUSTED)


async def _consume_rate_limit(redis: Any, user_id: str) -> None:
    """Charge one call to the same per-user budget as the web API."""
    settings = get_settings()
    try:
        await enforce_sliding_window(
            redis,
            key=user_rate_limit_key(user_id),
            max_requests=settings.rate_limit_max_requests,
            window=settings.rate_limit_window_seconds,
        )
    except RateLimitRefused as exc:
        raise _tool_error(exc.code) from exc


def _report_url(analysis_id: str) -> str | None:
    """Link to the full report on the web, in the same format as the emails."""
    base_url = get_settings().app_base_url
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"


def _to_verification(record: AnalysisHistoryItem) -> VerificationResult:
    """Translate the History row into the result the MCP client sees."""
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
        verdict=record.verdict if done else None,
        confidence=record.confidence if done else None,
        credibility=record.credibility if done else None,
        evidence_coverage=record.evidence_coverage if done else None,
        explanation=record.explanation if done else None,
        claims=record.claims or [],
        sources=record.sources or [],
        error_code=record.error_code if status == "failed" else None,
    )


RowT = TypeVar("RowT")


async def _read_analysis(
    read: Callable[..., Awaitable[RowT | None]], *, user_id: str, analysis_id: str
) -> RowT:
    """Read the user's Analysis, translating a DB failure or its absence to the contract."""
    try:
        # MCP is Pro only, whose History window has no limit.
        row = await read(user_id=user_id, analysis_id=analysis_id, visible_since=None)
    except DatabaseError as exc:
        raise _tool_error(ErrorCode.ANALYSIS_FETCH_FAILED) from exc
    if row is None:
        raise _tool_error(ErrorCode.ANALYSIS_NOT_FOUND)
    return row


async def _await_analysis(
    ctx: Context, *, user_id: str, analysis_id: str
) -> VerificationResult:
    """Poll only the status until the Analysis ends or the wait runs out, and read the report once."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + get_settings().mcp_tool_wait_seconds
    last_progress = -1

    while True:
        state = await _read_analysis(
            get_user_analysis_status, user_id=user_id, analysis_id=analysis_id
        )
        if state.status != "pending":
            record = await _read_analysis(
                get_user_analysis_by_id, user_id=user_id, analysis_id=analysis_id
            )
            return _to_verification(record)

        if state.stage in _ANALYSIS_STAGES:
            progress = _ANALYSIS_STAGES.index(state.stage)
            if progress > last_progress:
                last_progress = progress
                await ctx.report_progress(
                    progress, len(_ANALYSIS_STAGES), f"Running: {state.stage}"
                )

        if loop.time() >= deadline:
            return VerificationResult(
                status="pending",
                analysis_id=analysis_id,
                report_url=_report_url(analysis_id),
                stage=state.stage,
                message=(
                    "The analysis is still running. Call get_verification with "
                    "this analysis_id to keep waiting for the result."
                ),
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


def _to_evidence_result(job_id: str, result: dict) -> EvidenceSearchResult:
    """Translate the evidence job's result into the tool schema."""
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
                        abstract=hit.get("abstract"),
                    )
                    for hit in hits or []
                ],
            )
        )
    return EvidenceSearchResult(
        status="done",
        job_id=job_id,
        claims=claims,
        unsearched_claims=int(result.get("unsearched_claims") or 0),
    )


async def _await_evidence(
    ctx: Context, *, arq_pool: Any, job_id: str
) -> EvidenceSearchResult:
    """Poll the evidence job until it leaves a result or the wait runs out."""
    job = Job(job_id, arq_pool)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + get_settings().mcp_tool_wait_seconds
    last_progress = -1

    while True:
        try:
            info = await job.result_info()
            status = None if info is not None else await job.status()
        except (OSError, RedisError) as exc:
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE) from exc

        if info is not None:
            # A job that raised (e.g. arq's hard timeout) leaves no result dict.
            if not info.success or not isinstance(info.result, dict):
                raise _tool_error(ErrorCode.INTERNAL)
            if "error_code" in info.result:
                raise _tool_error(ErrorCode(info.result["error_code"]))
            return _to_evidence_result(job_id, info.result)

        if status == JobStatus.not_found:
            raise _tool_error(ErrorCode.EVIDENCE_SEARCH_NOT_FOUND)

        progress = 1 if status == JobStatus.in_progress else 0
        if progress > last_progress:
            last_progress = progress
            await ctx.report_progress(
                progress, 2, "Searching the literature" if progress else "Queued"
            )

        if loop.time() >= deadline:
            return EvidenceSearchResult(
                status="pending",
                job_id=job_id,
                message=(
                    "The evidence search is still running. Call get_evidence with "
                    "this job_id to keep waiting for the result."
                ),
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


def build_mcp_server(
    *, arq_pool: Any, redis: Any, analysis_intake: AnalysisIntake
) -> MCPServer:
    """Build the MCP server with Clerk OAuth authentication and its tools."""
    settings = get_settings()
    server = MCPServer(
        "VeriTrust",
        instructions=_INSTRUCTIONS,
        token_verifier=ClerkOAuthTokenVerifier(),
        # Strings, not AnyHttpUrl, so the SDK keeps the issuer without the trailing slash that would break RFC 8414.
        auth=AuthSettings.model_validate(
            {
                "issuer_url": settings.expected_issuer,
                "resource_server_url": settings.mcp_resource_url,
                # Clerk does not bind the token to the resource (RFC 8707), so the verifier checks issuer and client_id.
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
        """Run the full pipeline on a text or URL and wait for its result."""
        try:
            request = AnalysisRequest(
                text=text,
                url=url,  # type: ignore[arg-type]
                source_type=SourceType.URL if url is not None else SourceType.TEXT,
            )
        except ValidationError as exc:
            messages = "; ".join(str(error["msg"]) for error in exc.errors())
            raise ToolError(f"Invalid input: {messages}") from exc

        user_id, limits = await _pro_caller()
        await _consume_rate_limit(redis, user_id)

        # No email, since the MCP client gets the result in the call itself.
        submitter = Submitter(user_id=user_id, origin="mcp", limits=limits)
        try:
            analysis_id = await analysis_intake.submit(submitter, request)
        except AnalysisRefused as exc:
            raise _tool_error(exc.code) from exc

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
        """Wait for and return the status of one of the user's MCP analyses."""
        user_id, _ = await _pro_caller()
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
        """Enqueue the Evidence search in the worker and wait for its result."""
        user_id, limits = await _pro_caller()
        await _consume_rate_limit(redis, user_id)
        await _require_allowance(user_id, limits)

        job_id = uuid4().hex
        try:
            # The owner lives as long as the job can last plus how long its result is kept.
            await redis.set(
                _EVIDENCE_OWNER_KEY.format(job_id=job_id),
                user_id,
                ex=get_settings().analysis_job_timeout_seconds
                + EVIDENCE_RESULT_TTL_SECONDS,
            )
            # The worker records the search in user_id's Usage only if it ends with a result.
            job = await arq_pool.enqueue_job(
                "run_evidence_search", claim.strip(), user_id, _job_id=job_id
            )
        except (OSError, RedisError) as exc:
            logger.exception("[MCP] No se pudo encolar la búsqueda de evidencia")
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE) from exc
        if job is None:
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE)

        return await _await_evidence(ctx, arq_pool=arq_pool, job_id=job_id)

    @server.tool(
        description=_GET_EVIDENCE_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    async def get_evidence(
        ctx: Context,
        job_id: Annotated[
            str,
            Field(
                pattern=r"^[0-9a-f]{32}$",
                description="The job_id returned by search_evidence.",
            ),
        ],
    ) -> EvidenceSearchResult:
        """Wait for and return the result of one of the user's Evidence searches."""
        user_id, _ = await _pro_caller()
        try:
            owner = await redis.get(_EVIDENCE_OWNER_KEY.format(job_id=job_id))
        except (OSError, RedisError) as exc:
            raise _tool_error(ErrorCode.SERVICE_UNAVAILABLE) from exc

        # Someone else's search is treated like a missing one, so as not to reveal it exists.
        owner_id = owner.decode() if isinstance(owner, bytes) else owner
        if owner_id != user_id:
            raise _tool_error(ErrorCode.EVIDENCE_SEARCH_NOT_FOUND)
        return await _await_evidence(ctx, arq_pool=arq_pool, job_id=job_id)

    return server


def build_mcp_http_app(server: MCPServer) -> Starlette:
    """Return the server's Streamable HTTP app, limited to the configured hosts."""
    settings = get_settings()
    allowed_hosts = [urlparse(str(settings.mcp_resource_url)).netloc]
    if settings.is_development():
        allowed_hosts += ["localhost:*", "127.0.0.1:*"]
    return server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        # No in-memory session, so any replica serves old-protocol clients.
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=allowed_hosts,
            allowed_origins=settings.cors_origins(),
        ),
    )
