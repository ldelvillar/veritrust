"""Configuración centralizada de la aplicación, cargada y validada desde el entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsValidationError(RuntimeError):
    """La configuración de la aplicación es inválida o está incompleta."""


class Settings(BaseSettings):
    """Configuración de servicio leída del entorno (y de un .env si existe)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Base de datos
    database_url: str = ""

    # Entorno y CORS
    environment: str = "production"
    log_format: str = "text"  # "json" emite una línea JSON por registro (Cloud Logging)
    cors_allowed_origins: str = ""
    cors_allow_credentials: bool = True

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Modelos de Ollama por agente
    ollama_extractor_model: str = "llama3"
    ollama_translator_model: str = "translategemma"
    ollama_health_expert_model: str = "llama3.2"
    ollama_judge_model: str = "ministral-3:14b"

    # Tope por llamada al LLM; una llamada lenta falla en vez de agotar todo el job
    ollama_request_timeout_seconds: int = 240
    # Ventana de contexto (num_ctx) y tope de generación (num_predict) por agente
    ollama_extractor_num_ctx: int = 8192
    ollama_extractor_num_predict: int = 1024
    ollama_translator_num_ctx: int = 4096
    ollama_translator_num_predict: int = 2048
    ollama_health_expert_num_ctx: int = 8192
    ollama_health_expert_num_predict: int = 2048
    ollama_judge_num_ctx: int = 8192
    ollama_judge_num_predict: int = 512

    # Proveedor de los LLM: "ollama" (local), "mistral", "groq", "google" o "nvidia"
    llm_provider: str = "ollama"

    # Mistral; la api_key es obligatoria cuando llm_provider es "mistral"
    mistral_api_key: str | None = None
    mistral_extractor_model: str = "mistral-small-latest"
    mistral_translator_model: str = "mistral-small-latest"
    mistral_health_expert_model: str = "mistral-small-latest"
    mistral_judge_model: str = "mistral-small-latest"
    # La ventana de contexto la fija el servidor; solo se acota la generación
    mistral_max_tokens: int = 2048
    mistral_request_timeout_seconds: int = 60
    # Reintentos ante 429 y 5xx: el límite de peticiones del workspace corta las ráfagas
    mistral_max_retries: int = 5

    # Groq; la api_key es obligatoria cuando llm_provider es "groq"
    # Un modelo por rol: la cuota diaria de tokens de Groq es por modelo
    groq_api_key: str | None = None
    groq_extractor_model: str = "openai/gpt-oss-20b"
    groq_translator_model: str = "qwen/qwen3.8-27b"
    groq_health_expert_model: str = "qwen/qwen3.6-27b"
    groq_judge_model: str = "openai/gpt-oss-120b"
    # La ventana de contexto la fija el servidor; solo se acota la generación
    groq_max_tokens: int = 2048
    groq_request_timeout_seconds: int = 60
    # El plan gratuito corta a 8000 tokens/min; reintentar absorbe el 429
    groq_max_retries: int = 5
    # La cuota diaria de Groq es por modelo: rotar reparte la carga del juez
    groq_judge_model_rotation: str = ""

    # Google AI Studio; la api_key es obligatoria cuando llm_provider es "google"
    google_api_key: str | None = None
    google_extractor_model: str = "gemini-3.5-flash"
    google_translator_model: str = "gemini-3.5-flash"
    google_health_expert_model: str = "gemini-3.5-flash"
    google_judge_model: str = "gemini-3.5-flash"
    # La ventana de contexto la fija el servidor; solo se acota la generación
    google_max_tokens: int = 2048
    google_request_timeout_seconds: int = 60
    google_max_retries: int = 5

    # NVIDIA NIM; la api_key es obligatoria cuando llm_provider es "nvidia"
    nvidia_api_key: str | None = None
    nvidia_extractor_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_translator_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_health_expert_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_judge_model: str = "nvidia/nemotron-3-super-120b-a12b"
    # La ventana de contexto la fija el servidor; solo se acota la generación
    nvidia_max_tokens: int = 2048
    nvidia_request_timeout_seconds: int = 60

    # El informe del experto no decide la etiqueta: se apaga al evaluar para ahorrar tokens
    health_expert_explanation_enabled: bool = True

    # Prompts de los agentes (ruta a un YAML; si no se define, usa el del paquete)
    prompt_file_path: str | None = None

    # Europe PMC
    europepmc_base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    europepmc_timeout_seconds: int = 10

    # PubMed (NCBI E-utilities); la api_key solo amplía el límite de peticiones
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pubmed_timeout_seconds: int = 10
    pubmed_api_key: str | None = None

    # openFDA (fichas de medicamentos); la api_key solo amplía el límite de peticiones
    openfda_base_url: str = "https://api.fda.gov"
    openfda_timeout_seconds: int = 10
    openfda_api_key: str | None = None

    # AEMPS CIMA (medicamentos españoles: ficha técnica)
    cima_base_url: str = "https://cima.aemps.es/cima/rest"
    cima_timeout_seconds: int = 10

    # Redis / cola de trabajos (arq)
    redis_url: str = "redis://localhost:6379"

    # Cola de análisis (arq)
    analysis_job_timeout_seconds: int = 900  # 15 min: presupuesto del pipeline
    analysis_stale_after_seconds: int = 300  # 5 min: reaper, solo filas sin job vivo
    worker_max_jobs: int = 1  # Análisis concurrentes por worker

    # Rate limiting (POST /analysis, por usuario)
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 60

    # Rate limiting (POST /contact, por IP; perfil anti-spam de email)
    contact_rate_limit_max_requests: int = 5
    contact_rate_limit_window_seconds: int = 3600

    # Subida de archivos (POST /analysis/file)
    max_file_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Autenticación
    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    clerk_audience: str | None = None
    # Clave secreta del Backend API de Clerk, con la que se verifican las claves API (ak_…)
    clerk_secret_key: str = ""
    clerk_api_base_url: str = "https://api.clerk.com/v1"
    # Secreto de firma (whsec_…) del webhook con que Clerk avisa de las cuentas eliminadas
    clerk_webhook_secret: str = ""

    # Notificaciones por email (Resend); obligatorias fuera de desarrollo, donde sin api_key no se envía nada
    resend_api_key: str | None = None
    resend_from_email: str = ""
    resend_base_url: str = "https://api.resend.com"
    # Origen público del frontend, para construir el enlace al informe en el email
    app_base_url: str | None = None
    # Buzón del equipo al que llegan los formularios de contacto y demo; obligatorio en la web fuera de desarrollo
    contact_to_email: str = ""

    # Stripe (planes de pago): clave secreta, secreto de firma del webhook e ids de los precios Pro
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_pro_yearly: str = ""

    # Servidor MCP: URL pública del endpoint (termina en /mcp), identificador del recurso OAuth
    mcp_resource_url: str | None = None
    # Espera máxima de una llamada MCP antes de responder que el trabajo sigue en curso
    mcp_tool_wait_seconds: int = 240

    def cors_origins(self) -> list[str]:
        """Lista de orígenes permitidos; cae a localhost solo en desarrollo."""
        raw = self.cors_allowed_origins
        if not raw.strip() and self.environment.strip().lower() == "development":
            raw = "http://localhost:3000"
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def expected_issuer(self) -> str | None:
        """Issuer esperado de Clerk: explícito o derivado del JWKS URL."""
        issuer = (self.clerk_issuer or "").strip()
        if issuer:
            return issuer

        jwks_url = (self.clerk_jwks_url or "").strip()
        suffix = "/.well-known/jwks.json"
        if jwks_url.endswith(suffix):
            return jwks_url[: -len(suffix)]

        return None

    def expected_audience(self) -> str | list[str] | None:
        """Audiencia esperada de Clerk; lista si hay varias, str si hay una."""
        raw = (self.clerk_audience or "").strip()
        if not raw:
            return None

        audiences = [aud.strip() for aud in raw.split(",") if aud.strip()]
        return audiences if len(audiences) > 1 else audiences[0]

    def groq_judge_models(self) -> list[str]:
        """Modelos entre los que rota el juez; vacía significa no rotar."""
        return [
            m.strip() for m in self.groq_judge_model_rotation.split(",") if m.strip()
        ]

    def llm_provider_name(self) -> str:
        """Devuelve el proveedor de LLM normalizado en minúsculas."""
        return self.llm_provider.strip().lower()

    def validate_runtime(self, *, web: bool = True) -> None:
        """Valida la configuración obligatoria; el worker pasa web=False y omite lo exclusivo de la web."""
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
        if (
            web
            and self.environment.strip().lower() != "development"
            and not self.cors_origins()
        ):
            missing.append("CORS_ALLOWED_ORIGINS")
        if not self.app_base_url:
            missing.append("APP_BASE_URL")
        # Sin Resend, los avisos de análisis y los formularios de contacto fallarían en silencio
        if self.environment.strip().lower() != "development":
            if not (self.resend_api_key or "").strip():
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
    """Devuelve la configuración cacheada, construyéndola bajo demanda."""
    return Settings()
