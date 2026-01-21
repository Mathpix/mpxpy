from typing import Dict, Any, List, Optional

class StrokesResult:
    """Result from strokes/handwriting recognition.

    This class wraps the response from the /v3/strokes endpoint and provides
    convenient access to recognition results.

    Attributes:
        session_id: Session identifier.
        request_id: Request identifier.
        text: Recognized text.
        latex: LaTeX representation.
        latex_simplified: Simplified LaTeX.
        latex_styled: Styled LaTeX.
        latex_confidence: Confidence score (0-1).
        latex_confidence_rate: Confidence rate.
        position: Bounding box of recognized content.
        detection_map: Confidence scores for content types.
        detection_list: List of detected content types.
    """
    def __init__(self, result: Dict[str, Any]):
        """Initialize a StrokesResult from the API response.

        Args:
            result: The JSON response from /v3/strokes endpoint.
        """
        self.session_id: Optional[str] = result.get('session_id')
        self.request_id: Optional[str] = result.get('request_id')
        self.strokes_session_id: Optional[str] = result.get('strokes_session_id')
        self.text: Optional[str] = result.get('text')
        self.latex: Optional[str] = result.get('latex')
        self.latex_normal: Optional[str] = result.get('latex_normal')
        self.latex_simplified: Optional[str] = result.get('latex_simplified')
        self.latex_styled: Optional[str] = result.get('latex_styled')
        self.latex_confidence: Optional[float] = result.get('latex_confidence')
        self.latex_confidence_rate: Optional[float] = result.get('latex_confidence_rate')
        self.position: Optional[Dict[str, int]] = result.get('position')
        self.detection_map: Optional[Dict[str, float]] = result.get('detection_map')
        self.detection_list: Optional[List[str]] = result.get('detection_list')
        self.image_width: Optional[int] = result.get('image_width')
        self.image_height: Optional[int] = result.get('image_height')
        self.version: Optional[str] = result.get('version')
        self.error: Optional[str] = result.get('error')
        self.error_info: Optional[Dict[str, Any]] = result.get('error_info')
        self._raw = result

    def __repr__(self) -> str:
        if self.error:
            return f"StrokesResult(error={self.error!r})"
        return f"StrokesResult(latex={self.latex!r}, confidence={self.latex_confidence})"

    def to_dict(self) -> Dict[str, Any]:
        """Return the raw API response as a dictionary."""
        return self._raw
