from __future__ import annotations

class ParityNotImplementedError(NotImplementedError):
    """Raised when an R export is registered but not yet semantically ported."""

class ReportText(list):
    """Character-vector-like report text with a template marker."""
    def __init__(self, lines, template: str):
        super().__init__(str(x) for x in lines)
        self.template = template

    def __str__(self) -> str:
        return "\n".join(self)
