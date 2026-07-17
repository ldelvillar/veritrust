"""Esquemas de las valoraciones de veredicto que envían los usuarios."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SuggestedVerdict = Literal["real", "fake", "uncertain"]


class FeedbackRequest(BaseModel):
    """Valoración de un veredicto: confirmación o corrección con comentario opcional."""

    is_correct: bool
    suggested_verdict: Optional[SuggestedVerdict] = None
    comment: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _normalize(self) -> "FeedbackRequest":
        """Recorta el comentario y descarta la corrección si el veredicto se confirma."""
        if self.comment is not None:
            self.comment = self.comment.strip() or None
        if self.is_correct:
            self.suggested_verdict = None
            self.comment = None
        return self


class AnalysisFeedback(BaseModel):
    """Valoración activa de un análisis tal y como la consume el frontend."""

    is_correct: bool
    suggested_verdict: Optional[SuggestedVerdict] = None
    comment: Optional[str] = None
    created_at: str


class FeedbackResponse(BaseModel):
    """Respuesta al guardar una valoración de veredicto."""

    status: str
    feedback: AnalysisFeedback
