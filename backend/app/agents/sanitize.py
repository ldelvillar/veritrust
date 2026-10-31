"""User data markers and their neutralisation, shared by the agents."""

USER_INPUT_START = "<<USER_INPUT>>"
USER_INPUT_END = "<<END>>"


def neutralize_delimiters(text: str) -> str:
    """Stop user text from forging the data markers."""
    return text.replace(USER_INPUT_START, "").replace(USER_INPUT_END, "")
