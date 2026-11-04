"""Link to an Analysis report, the only place the backend knows the frontend route."""


def build_report_url(base_url: str, analysis_id: str) -> str:
    """Build the link to the Analysis report in the frontend."""
    # Mirrors the frontend route frontend/src/app/app/analisis/[id]/page.tsx.
    return f"{base_url.rstrip('/')}/app/analisis/{analysis_id}"
