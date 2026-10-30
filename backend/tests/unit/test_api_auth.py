"""Tests unitarios para la autenticacion (get_current_user, el cliente JWKS y las claves API de Clerk)."""

import io
import json
import time
import urllib.request
from urllib.error import URLError

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from app.api.dependencies import get_current_user as get_user_module
from app.core import api_keys as api_keys_module
from app.core import jwks as jwks_module
from app.core.config import Settings

_JWKS_URL = "https://tenant.clerk.accounts.dev/.well-known/jwks.json"
_CLERK_API_URL = "https://api.clerk.test/v1"
_CLERK_SECRET_KEY = "sk_test_dummy"
_API_KEY = "ak_test_dummy_secret"
_KEY_OWNER = "user_2xhFjEI5X2qWRvtV13BzSj8H6Dk"


def _make_settings(**overrides) -> Settings:
    """Construye Settings deterministas, ignorando .env y el entorno real."""
    base: dict[str, object] = {
        "database_url": "postgresql://user:pass@localhost:5432/db",
        "environment": "development",
        "cors_allowed_origins": "http://localhost:3000",
        "clerk_jwks_url": None,
        "clerk_issuer": None,
        "clerk_audience": "my-api",
        "clerk_secret_key": _CLERK_SECRET_KEY,
        "clerk_api_base_url": _CLERK_API_URL,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _use_settings(monkeypatch, **overrides) -> Settings:
    """Hace que get_current_user, el cliente JWKS y las claves API usen una configuración controlada."""
    settings = _make_settings(**overrides)
    monkeypatch.setattr(get_user_module, "get_settings", lambda: settings)
    monkeypatch.setattr(jwks_module, "get_settings", lambda: settings)
    monkeypatch.setattr(api_keys_module, "get_settings", lambda: settings)
    return settings


def test_get_current_user_returns_500_if_no_jwks_url_is_configured(monkeypatch):
    _use_settings(monkeypatch, clerk_jwks_url=None)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer irrelevant-token")

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "AUTH_MISCONFIGURED"


def test_get_expected_issuer_uses_explicit_clerk_issuer(monkeypatch):
    _use_settings(monkeypatch, clerk_issuer="https://my-tenant.clerk.accounts.dev")

    assert (
        get_user_module._get_expected_issuer() == "https://my-tenant.clerk.accounts.dev"
    )


def test_get_expected_issuer_falls_back_to_jwks_url(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer=None,
        clerk_jwks_url="https://my-tenant.clerk.accounts.dev/.well-known/jwks.json",
    )

    assert (
        get_user_module._get_expected_issuer() == "https://my-tenant.clerk.accounts.dev"
    )


def test_get_expected_issuer_raises_500_when_not_configured(monkeypatch):
    _use_settings(monkeypatch, clerk_issuer=None, clerk_jwks_url=None)

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_expected_issuer()

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "AUTH_MISCONFIGURED"


def test_get_expected_audience_parses_single_audience(monkeypatch):
    _use_settings(monkeypatch, clerk_audience="my-api")

    assert get_user_module._get_expected_audience() == "my-api"


def test_get_expected_audience_parses_multiple_audiences(monkeypatch):
    _use_settings(monkeypatch, clerk_audience="my-api, my-other-api")

    assert get_user_module._get_expected_audience() == ["my-api", "my-other-api"]


def test_get_expected_audience_raises_500_when_not_configured(monkeypatch):
    _use_settings(monkeypatch, clerk_audience="")

    with pytest.raises(HTTPException) as exc:
        get_user_module._get_expected_audience()

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "AUTH_MISCONFIGURED"


def test_get_current_user_returns_payload_when_token_is_valid(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )

    def _fake_decode(token, signing_key, algorithms, audience, issuer, leeway, options):
        assert token == "valid-token"
        assert signing_key == "signing-key"
        assert algorithms == ["RS256"]
        assert audience == "my-api"
        assert issuer == "https://my-tenant.clerk.accounts.dev"
        assert leeway == 10
        assert options == {"verify_aud": True, "verify_iss": True}
        return {"sub": "user_1", "sid": "session_1"}

    monkeypatch.setattr(get_user_module, "get_signing_key", lambda _: "signing-key")
    monkeypatch.setattr(get_user_module.jwt, "decode", _fake_decode)

    payload = get_user_module.get_current_user("Bearer valid-token")

    assert payload["sub"] == "user_1"
    assert payload["sid"] == "session_1"


def test_get_current_user_rejects_missing_authorization_header():
    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(None)

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "UNAUTHENTICATED"


def test_get_current_user_rejects_invalid_auth_header():
    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Token abc")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN"


def test_get_current_user_returns_401_when_token_is_expired(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )
    monkeypatch.setattr(get_user_module, "get_signing_key", lambda _: "signing-key")

    def _raise_expired(*args, **kwargs):
        raise get_user_module.jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_expired)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer expired-token")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "EXPIRED_TOKEN"


def test_get_current_user_returns_401_when_token_is_invalid(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )
    monkeypatch.setattr(get_user_module, "get_signing_key", lambda _: "signing-key")

    def _raise_invalid(*args, **kwargs):
        raise get_user_module.jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_invalid)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer invalid-token")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN"


def _use_jwks(monkeypatch, serve) -> list[str]:
    """Sirve el JWKS de Clerk con ``serve`` al cliente real de producción y cuenta las descargas."""
    _use_settings(
        monkeypatch,
        clerk_jwks_url=_JWKS_URL,
        clerk_issuer="https://tenant.clerk.accounts.dev",
    )
    downloads: list[str] = []

    def _urlopen(request, timeout=None, context=None):
        downloads.append(request.full_url)
        return io.BytesIO(json.dumps(serve()).encode())

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    client = jwks_module._get_jwks_client.__wrapped__(_JWKS_URL)
    monkeypatch.setattr(jwks_module, "_get_jwks_client", lambda url: client)
    return downloads


def _rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwk(key, kid: str) -> dict:
    """Clave pública en formato JWK con su kid, como la publica Clerk."""
    return {**RSAAlgorithm.to_jwk(key.public_key(), as_dict=True), "kid": kid}


def _token(kid: str) -> str:
    return jwt.encode(
        {"sub": "user_1"}, _rsa_key(), algorithm="RS256", headers={"kid": kid}
    )


def test_get_current_user_returns_401_when_the_signing_key_is_unknown(monkeypatch):
    jwks = {"keys": [_jwk(_rsa_key(), "clerk-key")]}
    _use_jwks(monkeypatch, lambda: jwks)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(f"Bearer {_token('forged')}")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN"


def test_get_current_user_returns_503_when_the_jwks_is_unreachable(monkeypatch):
    def _unreachable():
        raise URLError("connection refused")

    _use_jwks(monkeypatch, _unreachable)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(f"Bearer {_token('clerk-key')}")

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "SERVICE_UNAVAILABLE"


def test_unknown_kids_refetch_the_jwks_at_most_once_per_cooldown(monkeypatch):
    jwks = {"keys": [_jwk(_rsa_key(), "clerk-key")]}
    downloads = _use_jwks(monkeypatch, lambda: jwks)

    for kid in ("forged-1", "forged-2", "forged-3"):
        with pytest.raises(HTTPException) as exc:
            get_user_module.get_current_user(f"Bearer {_token(kid)}")
        assert exc.value.status_code == 401

    # Una descarga para llenar la caché y un único refresco forzado dentro del cooldown.
    assert len(downloads) == 2


def test_a_rotated_signing_key_is_picked_up_once_the_cooldown_passes(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(jwks_module, "monotonic", lambda: clock[0])
    jwks = {"keys": [_jwk(_rsa_key(), "old-key")]}
    _use_jwks(monkeypatch, lambda: jwks)
    client = jwks_module._get_jwks_client(_JWKS_URL)

    with pytest.raises(jwt.PyJWKClientError):
        client.get_signing_key("new-key")
    # Clerk publica la clave nueva, pero el refresco forzado ya se gastó en este intervalo.
    jwks["keys"].append(_jwk(_rsa_key(), "new-key"))
    with pytest.raises(jwt.PyJWKClientError):
        client.get_signing_key("new-key")

    clock[0] += jwks_module.JWKS_REFRESH_COOLDOWN_SECONDS
    assert client.get_signing_key("new-key").key_id == "new-key"


def _api_key_record(**overrides) -> dict:
    """Cuerpo 200 de POST /api_keys/verify, con la forma del OpenAPI del Backend API de Clerk."""
    record: dict[str, object] = {
        "object": "api_key",
        "id": "ak_3beecc9c60adb5f9b850e91a8ee1e992",
        "type": "api_key",
        "subject": _KEY_OWNER,
        "name": "CMS de Acme",
        "description": None,
        "claims": None,
        "scopes": [],
        "revoked": False,
        "revocation_reason": None,
        "expired": False,
        "expiration": None,
        "created_by": None,
        "last_used_at": None,
        "created_at": 1716883200000,
        "updated_at": 1716883200000,
    }
    record.update(overrides)
    return record


_CLERK_ERROR = {
    "errors": [{"message": "not found", "long_message": "not found", "code": "x"}]
}


def _use_clerk(monkeypatch, respond) -> list[httpx.Request]:
    """Atiende con ``respond`` las peticiones al Backend API de Clerk y devuelve las recibidas."""
    _use_settings(monkeypatch)
    monkeypatch.setattr(api_keys_module, "_verified", {})
    received: list[httpx.Request] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return respond(request)

    client = httpx.Client(transport=httpx.MockTransport(_handle))
    monkeypatch.setattr(api_keys_module.httpx, "post", client.post)
    return received


def test_an_api_key_maps_to_the_user_that_owns_it(monkeypatch):
    received = _use_clerk(
        monkeypatch, lambda _: httpx.Response(200, json=_api_key_record())
    )

    user = get_user_module.get_current_user(f"Bearer {_API_KEY}")

    assert user == {"sub": _KEY_OWNER}
    [request] = received
    assert request.method == "POST"
    assert str(request.url) == f"{_CLERK_API_URL}/api_keys/verify"
    assert request.headers["authorization"] == f"Bearer {_CLERK_SECRET_KEY}"
    assert json.loads(request.content) == {"secret": _API_KEY}


@pytest.mark.parametrize(
    ("status", "body"),
    [
        pytest.param(404, _CLERK_ERROR, id="unknown"),
        pytest.param(400, _CLERK_ERROR, id="malformed"),
        pytest.param(200, _api_key_record(revoked=True), id="revoked"),
        pytest.param(200, _api_key_record(expired=True), id="expired"),
        pytest.param(
            200,
            _api_key_record(subject="org_2xhFjEI5X2qWRvtV13BzSj8H6Dk"),
            id="organization-scoped",
        ),
    ],
)
def test_an_unusable_api_key_returns_401(monkeypatch, status, body):
    _use_clerk(monkeypatch, lambda _: httpx.Response(status, json=body))

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(f"Bearer {_API_KEY}")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN"


def _refuse_connection(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


@pytest.mark.parametrize(
    "respond",
    [
        pytest.param(_refuse_connection, id="connection-refused"),
        pytest.param(lambda _: httpx.Response(503), id="server-error"),
        pytest.param(lambda _: httpx.Response(429), id="rate-limited"),
    ],
)
def test_an_api_key_returns_503_when_clerk_is_unreachable(monkeypatch, respond):
    _use_clerk(monkeypatch, respond)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(f"Bearer {_API_KEY}")

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(401, id="secret-key-invalid"),
        pytest.param(403, id="api-keys-not-enabled"),
    ],
)
def test_an_api_key_returns_500_when_clerk_refuses_our_setup(monkeypatch, status):
    _use_clerk(monkeypatch, lambda _: httpx.Response(status, json=_CLERK_ERROR))

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(f"Bearer {_API_KEY}")

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "AUTH_MISCONFIGURED"


def test_a_verified_api_key_is_served_from_cache_until_its_ttl_passes(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(api_keys_module, "monotonic", lambda: clock[0])
    clerk = {"response": lambda: httpx.Response(200, json=_api_key_record())}
    received = _use_clerk(monkeypatch, lambda _: clerk["response"]())

    get_user_module.get_current_user(f"Bearer {_API_KEY}")
    # Revocada en Clerk: la caché la sigue aceptando hasta que caduque su entrada.
    clerk["response"] = lambda: httpx.Response(404, json=_CLERK_ERROR)
    assert get_user_module.get_current_user(f"Bearer {_API_KEY}") == {"sub": _KEY_OWNER}
    assert len(received) == 1

    clock[0] += api_keys_module.VERIFIED_KEY_TTL_SECONDS
    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user(f"Bearer {_API_KEY}")
    assert exc.value.status_code == 401
    assert len(received) == 2


def test_a_session_jwt_is_still_verified_locally_without_calling_clerk(monkeypatch):
    received = _use_clerk(
        monkeypatch, lambda _: httpx.Response(200, json=_api_key_record())
    )
    key = _rsa_key()
    jwks = {"keys": [_jwk(key, "clerk-key")]}
    _use_jwks(monkeypatch, lambda: jwks)
    session_token = jwt.encode(
        {
            "sub": "user_1",
            "aud": "my-api",
            "iss": "https://tenant.clerk.accounts.dev",
            "exp": int(time.time()) + 60,
        },
        key,
        algorithm="RS256",
        headers={"kid": "clerk-key"},
    )

    user = get_user_module.get_current_user(f"Bearer {session_token}")

    assert user["sub"] == "user_1"
    assert received == []


def test_get_current_user_returns_500_for_invalid_key_format(monkeypatch):
    _use_settings(
        monkeypatch,
        clerk_issuer="https://my-tenant.clerk.accounts.dev",
        clerk_audience="my-api",
    )
    monkeypatch.setattr(get_user_module, "get_signing_key", lambda _: "bad-key")

    def _raise_type_error(*args, **kwargs):
        raise TypeError("Expecting a PEM-formatted key.")

    monkeypatch.setattr(get_user_module.jwt, "decode", _raise_type_error)

    with pytest.raises(HTTPException) as exc:
        get_user_module.get_current_user("Bearer token")

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "AUTH_MISCONFIGURED"
