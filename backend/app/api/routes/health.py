"""Endpoint de readiness para load balancers."""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/healthz")
async def healthz(request: Request):
    """Devuelve 503 si el grafo multiagente no se inicializó correctamente."""
    if getattr(request.app.state, "verification_system", None) is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}
