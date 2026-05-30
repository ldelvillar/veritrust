"""Configuración centralizada de la aplicación, cargada y validada desde el entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsValidationError(RuntimeError):
    """La configuración de la aplicación es inválida o está incompleta."""


def _normalize_pem_key(key: str | None) -> str | None:
    """Normaliza claves PEM definidas en variables de entorno con \\n escapados."""
    if not key:
        return None
    return key.replace("\\n", "\n").strip()


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
    cors_allowed_origins: str = ""
    cors_allow_credentials: bool = True

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Modelo BERT detector (ruta local; si no se define, se autodetecta)
    fake_news_model_path: str | None = None

    # Redis / cola de trabajos (arq)
    redis_url: str = "redis://localhost:6379"

    # Rate limiting (POST /analysis, por usuario)
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 60

    # Autenticación
    clerk_pem_public_key: str | None = None
    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    clerk_audience: str | None = None

    def cors_origins(self) -> list[str]:
        """Lista de orígenes permitidos; cae a localhost solo en desarrollo."""
        raw = self.cors_allowed_origins
        if not raw.strip() and self.environment.strip().lower() == "development":
            raw = "http://localhost:3000"
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def pem_public_key(self) -> str | None:
        """Clave PEM normalizada, o None si no está configurada."""
        return _normalize_pem_key(self.clerk_pem_public_key)

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

    def validate_runtime(self, *, require_cors: bool = True) -> None:
        """Valida la configuración obligatoria. Invocado en el startup del lifespan.

        ``require_cors`` solo aplica al proceso web; el worker no sirve HTTP y no
        tiene configuración de CORS, así que la omite.
        """
        missing: list[str] = []

        if not self.database_url.strip():
            missing.append("DATABASE_URL")
        if not self.clerk_jwks_url and not self.pem_public_key:
            missing.append("CLERK_JWKS_URL o CLERK_PEM_PUBLIC_KEY")
        if self.expected_issuer is None:
            missing.append("CLERK_ISSUER o un CLERK_JWKS_URL válido")
        if self.expected_audience() is None:
            missing.append("CLERK_AUDIENCE")
        if (
            require_cors
            and self.environment.strip().lower() != "development"
            and not self.cors_origins()
        ):
            missing.append("CORS_ALLOWED_ORIGINS")

        if missing:
            raise SettingsValidationError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )

        if require_cors and self.cors_allow_credentials and "*" in self.cors_origins():
            raise SettingsValidationError(
                "CORS_ALLOWED_ORIGINS no puede contener '*' cuando "
                "allow_credentials=True"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuración cacheada, construyéndola bajo demanda."""
    return Settings()
