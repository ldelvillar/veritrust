"""Centralised application configuration, loaded and validated from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsValidationError(RuntimeError):
    """The application configuration is invalid or incomplete."""


class Settings(BaseSettings):
    """Service configuration read from the environment and from a .env file if present."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = ""

    environment: str = "production"
    log_format: str = "text"  # "json" emits one JSON line per record (Cloud Logging).
    cors_allowed_origins: str = ""
    cors_allow_credentials: bool = True

    ollama_base_url: str = "http://localhost:11434"

    ollama_extractor_model: str = "llama3"
    ollama_translator_model: str = "translategemma"
    ollama_health_expert_model: str = "llama3.2"
    ollama_judge_model: str = "ministral-3:14b"

    # Per-call LLM cap, so a slow call fails instead of exhausting the whole job.
    ollama_request_timeout_seconds: int = 240
    # Context window (num_ctx) and generation cap (num_predict) per agent.
    ollama_extractor_num_ctx: int = 8192
    ollama_extractor_num_predict: int = 1024
    ollama_translator_num_ctx: int = 4096
    ollama_translator_num_predict: int = 2048
    ollama_health_expert_num_ctx: int = 8192
    ollama_health_expert_num_predict: int = 2048
    ollama_judge_num_ctx: int = 8192
    ollama_judge_num_predict: int = 512

    # LLM provider: "ollama" (local), "mistral", "groq", "google" or "nvidia".
    llm_provider: str = "ollama"

    # The api_key is required when llm_provider is "mistral".
    mistral_api_key: str | None = None
    mistral_extractor_model: str = "mistral-small-latest"
    mistral_translator_model: str = "mistral-small-latest"
    mistral_health_expert_model: str = "mistral-small-latest"
    mistral_judge_model: str = "mistral-small-latest"
    # The server fixes the context window, so only generation is capped.
    mistral_max_tokens: int = 2048
    mistral_request_timeout_seconds: int = 60
    # Retries on 429 and 5xx, since the workspace request limit cuts bursts.
    mistral_max_retries: int = 5

    # The api_key is required when llm_provider is "groq", and each role has its own model because Groq's daily token quota is per model.
    groq_api_key: str | None = None
    groq_extractor_model: str = "openai/gpt-oss-20b"
    groq_translator_model: str = "qwen/qwen3.8-27b"
    groq_health_expert_model: str = "qwen/qwen3.6-27b"
    groq_judge_model: str = "openai/gpt-oss-120b"
    # The server fixes the context window, so only generation is capped.
    groq_max_tokens: int = 2048
    groq_request_timeout_seconds: int = 60
    # The free plan caps at 8000 tokens/min, so retrying absorbs the 429.
    groq_max_retries: int = 5
    # Groq's daily quota is per model, so rotating spreads the judge's load.
    groq_judge_model_rotation: str = ""

    # The api_key is required when llm_provider is "google".
    google_api_key: str | None = None
    google_extractor_model: str = "gemini-3.5-flash"
    google_translator_model: str = "gemini-3.5-flash"
    google_health_expert_model: str = "gemini-3.5-flash"
    google_judge_model: str = "gemini-3.5-flash"
    # The server fixes the context window, so only generation is capped.
    google_max_tokens: int = 2048
    google_request_timeout_seconds: int = 60
    google_max_retries: int = 5

    # The api_key is required when llm_provider is "nvidia".
    nvidia_api_key: str | None = None
    nvidia_extractor_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_translator_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_health_expert_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_judge_model: str = "nvidia/nemotron-3-super-120b-a12b"
    # The server fixes the context window, so only generation is capped.
    nvidia_max_tokens: int = 2048
    nvidia_request_timeout_seconds: int = 60

    # The expert's report does not decide the label, so it is turned off during evaluation to save tokens.
    health_expert_explanation_enabled: bool = True

    # Path to an agent prompts YAML, falling back to the packaged one when unset.
    prompt_file_path: str | None = None

    europepmc_base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    europepmc_timeout_seconds: int = 10

    # The api_key only raises the request limit.
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pubmed_timeout_seconds: int = 10
    pubmed_api_key: str | None = None

    # The api_key only raises the request limit.
    openfda_base_url: str = "https://api.fda.gov"
    openfda_timeout_seconds: int = 10
    openfda_api_key: str | None = None

    cima_base_url: str = "https://cima.aemps.es/cima/rest"
    cima_timeout_seconds: int = 10

    redis_url: str = "redis://localhost:6379"

    analysis_job_timeout_seconds: int = 900  # 15 min pipeline budget.
    analysis_stale_after_seconds: int = (
        300  # The reaper only fails rows with no live job.
    )
    worker_max_jobs: int = 1

    # Per-user rate limit for POST /analysis.
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 60

    # Per-IP rate limit for POST /contact, an email anti-spam profile.
    contact_rate_limit_max_requests: int = 5
    contact_rate_limit_window_seconds: int = 3600

    max_file_bytes: int = 10 * 1024 * 1024

    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    clerk_audience: str | None = None
    # Clerk Backend API secret key, used to verify API keys (ak_…).
    clerk_secret_key: str = ""
    clerk_api_base_url: str = "https://api.clerk.com/v1"
    # Signing secret (whsec_…) of the webhook Clerk uses to report deleted accounts.
    clerk_webhook_secret: str = ""

    # Resend email notifications, required outside development, where nothing is sent without an api_key.
    resend_api_key: str = ""
    resend_from_email: str = ""
    resend_base_url: str = "https://api.resend.com"
    # Public frontend origin, to build the report link in the email.
    app_base_url: str | None = None
    # Team inbox for the contact and demo forms, required by the web process outside development.
    contact_to_email: str = ""

    # Stripe secret key, webhook signing secret and Pro price ids.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_pro_yearly: str = ""

    # Public URL of the MCP endpoint (ends in /mcp), the OAuth resource identifier.
    mcp_resource_url: str | None = None
    # How long an MCP call waits before answering that the job is still running.
    mcp_tool_wait_seconds: int = 240

    def cors_origins(self) -> list[str]:
        """List of allowed origins, falling back to localhost only in development."""
        raw = self.cors_allowed_origins
        if not raw.strip() and self.is_development():
            raw = "http://localhost:3000"
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def expected_issuer(self) -> str | None:
        """Expected Clerk issuer, explicit or derived from the JWKS URL."""
        issuer = (self.clerk_issuer or "").strip()
        if issuer:
            return issuer

        jwks_url = (self.clerk_jwks_url or "").strip()
        suffix = "/.well-known/jwks.json"
        if jwks_url.endswith(suffix):
            return jwks_url[: -len(suffix)]

        return None

    def expected_audience(self) -> str | list[str] | None:
        """Expected Clerk audience, a list if there are several and a str if there is one."""
        raw = (self.clerk_audience or "").strip()
        if not raw:
            return None

        audiences = [aud.strip() for aud in raw.split(",") if aud.strip()]
        return audiences if len(audiences) > 1 else audiences[0]

    def groq_judge_models(self) -> list[str]:
        """Models the judge rotates between, where empty means no rotation."""
        return [
            m.strip() for m in self.groq_judge_model_rotation.split(",") if m.strip()
        ]

    def is_development(self) -> bool:
        """Tell whether the process runs with ENVIRONMENT=development."""
        return self.environment.strip().lower() == "development"

    def llm_provider_name(self) -> str:
        """Return the LLM provider normalised to lowercase."""
        return self.llm_provider.strip().lower()

    def validate_runtime(self, *, web: bool = True) -> None:
        """Validate the required configuration, where the worker passes web=False and skips web-only settings."""
        missing: list[str] = []

        provider = self.llm_provider_name()
        if provider == "mistral" and not (self.mistral_api_key or "").strip():
            missing.append("MISTRAL_API_KEY")
        if provider == "groq" and not (self.groq_api_key or "").strip():
            missing.append("GROQ_API_KEY")
        if provider == "google" and not (self.google_api_key or "").strip():
            missing.append("GOOGLE_API_KEY")
        if provider == "nvidia" and not (self.nvidia_api_key or "").strip():
            missing.append("NVIDIA_API_KEY")

        if not self.database_url.strip():
            missing.append("DATABASE_URL")
        if not self.clerk_jwks_url:
            missing.append("CLERK_JWKS_URL")
        if self.expected_issuer is None:
            missing.append("CLERK_ISSUER o un CLERK_JWKS_URL válido")
        if self.expected_audience() is None:
            missing.append("CLERK_AUDIENCE")
        if not self.clerk_secret_key.strip():
            missing.append("CLERK_SECRET_KEY")
        if web and not self.is_development() and not self.cors_origins():
            missing.append("CORS_ALLOWED_ORIGINS")
        if not self.app_base_url:
            missing.append("APP_BASE_URL")
        # Without Resend, analysis notices would be silently lost and the forms would answer 503.
        if not self.is_development():
            if not self.resend_api_key.strip():
                missing.append("RESEND_API_KEY")
            if not self.resend_from_email.strip():
                missing.append("RESEND_FROM_EMAIL")
            if web and not self.contact_to_email.strip():
                missing.append("CONTACT_TO_EMAIL")
        if web:
            for name in (
                "stripe_secret_key",
                "stripe_webhook_secret",
                "stripe_price_pro_monthly",
                "stripe_price_pro_yearly",
                "clerk_webhook_secret",
            ):
                if not getattr(self, name).strip():
                    missing.append(name.upper())
        if web and not (self.mcp_resource_url or "").strip():
            missing.append("MCP_RESOURCE_URL")

        if missing:
            raise SettingsValidationError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )

        if web and not (self.mcp_resource_url or "").rstrip("/").endswith("/mcp"):
            raise SettingsValidationError("MCP_RESOURCE_URL debe terminar en /mcp")

        if web and self.cors_allow_credentials and "*" in self.cors_origins():
            raise SettingsValidationError(
                "CORS_ALLOWED_ORIGINS no puede contener '*' cuando "
                "allow_credentials=True"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached configuration, building it on demand."""
    return Settings()
