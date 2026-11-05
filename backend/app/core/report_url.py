"""Link to an Analysis report in the frontend, which the backend builds only here."""

from app.core.config import get_settings


def build_report_url(analysis_id: str) -> str:
    """Build the link to the Analysis report in the frontend."""
    # Mirrors the frontend route frontend/src/app/app/analisis/[id]/page.tsx.
    return f"{get_settings().app_base_url}/app/analisis/{analysis_id}"
