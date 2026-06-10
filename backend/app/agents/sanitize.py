"""Marcadores de datos del usuario y su neutralización, compartidos por los agentes."""

USER_INPUT_START = "<<USER_INPUT>>"
USER_INPUT_END = "<<END>>"


def neutralize_delimiters(text: str) -> str:
    """Impide que el texto del usuario falsifique los marcadores de datos."""
    return text.replace(USER_INPUT_START, "").replace(USER_INPUT_END, "")
