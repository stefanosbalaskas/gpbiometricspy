"""Researcher-facing error classification and remediation for Studio.

This module is deliberately presentation-only. It does not catch, replace, or
reinterpret scientific exceptions. It maps already-caught UI failures to stable,
privacy-safe recovery guidance while preserving local/private diagnostic detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from studio.config import studio_runtime_config
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from config import studio_runtime_config


@dataclass(frozen=True)
class ErrorGuidance:
    """Stable presentation metadata for one class of Studio failure."""

    code: str
    category: str
    title: str
    next_action: str


_GUIDANCE = {
    "input": ErrorGuidance(
        code="GP-STUDIO-INPUT",
        category="input",
        title="Input or selection needs attention.",
        next_action=(
            "Review the required file or selections, supported columns and numeric ranges, "
            "then retry the step."
        ),
    ),
    "prerequisite": ErrorGuidance(
        code="GP-STUDIO-PREREQ",
        category="prerequisite",
        title="A workflow prerequisite is not complete.",
        next_action=(
            "Load the project, run foundation QC, and complete the upstream analysis or "
            "alignment step shown by Studio before retrying."
        ),
    ),
    "identity": ErrorGuidance(
        code="GP-STUDIO-IDENTITY",
        category="identity",
        title="Project or resource identity verification failed.",
        next_action=(
            "Use the exact dataset or secondary resource that created the recipe/replay; "
            "do not bypass fingerprint validation."
        ),
    ),
    "resource": ErrorGuidance(
        code="GP-STUDIO-RESOURCE",
        category="resource",
        title="A required external resource is unavailable or unreadable.",
        next_action=(
            "Re-select the required event log, target stream, recipe or supported file and "
            "retry. For replay, verify that the configured resource is the intended one."
        ),
    ),
    "analysis": ErrorGuidance(
        code="GP-STUDIO-ANALYSIS",
        category="analysis",
        title="The analysis step could not complete.",
        next_action=(
            "Review module prerequisites, selected signals, QC, sampling/timing assumptions "
            "and expert parameters before retrying."
        ),
    ),
    "unknown": ErrorGuidance(
        code="GP-STUDIO-UNKNOWN",
        category="unknown",
        title="The step could not complete.",
        next_action=(
            "Review the current inputs and Quality Control. If the problem persists, run "
            "gpbiometricspy-studio-doctor and retain its privacy-safe diagnostics."
        ),
    ),
}


def classify_failure(message: str, *, context: str = "") -> ErrorGuidance:
    """Classify a caught UI failure using message semantics only.

    The returned guidance is static and never contains substrings copied from the
    supplied message, which keeps the guidance object safe to expose publicly.
    """

    text = f"{context} {message}".casefold()

    identity_terms = (
        "fingerprint mismatch",
        "identity mismatch",
        "sha256",
        "sha-256",
        "source fingerprint",
        "resource fingerprint",
        "does not match the loaded dataset",
        "does not match this dataset",
    )
    if any(term in text for term in identity_terms):
        return _GUIDANCE["identity"]

    # The primary dataset import is an input problem; secondary project resources
    # are classified separately so remediation can name replay/resource handling.
    if "import failed" in text or "gazepoint csv" in text or "gazepoint txt" in text:
        return _GUIDANCE["input"]

    resource_terms = (
        "event log",
        "event-log",
        "target stream",
        "secondary stream",
        "secondary biometric",
        "project recipe",
        "recipe upload",
        "aoi definition",
        "external resource",
    )
    if any(term in text for term in resource_terms):
        return _GUIDANCE["resource"]

    prerequisite_terms = (
        "load a dataset",
        "load data before",
        "foundation qc",
        "run qc",
        "qc required",
        "alignment required",
        "events & alignment required",
        "complete events & alignment",
        "before running",
        "no analysis result",
        "analysis has not run",
        "not available until",
    )
    if any(term in text for term in prerequisite_terms):
        return _GUIDANCE["prerequisite"]

    # Input classification requires validation/selection language. Bare parameter
    # names such as "threshold" may appear inside diagnostic payloads and must not
    # override an explicit analysis-failure context.
    input_terms = (
        "select ",
        "selected ",
        "choose ",
        " column",
        "numeric",
        "must be positive",
        "must be non-empty",
        "characters or fewer",
        "sampling rate",
        "window size",
        "formula",
        "grouping",
        "unsupported",
    )
    if any(term in text for term in input_terms):
        return _GUIDANCE["input"]

    analysis_terms = (
        "analysis failed",
        "workflow failed",
        "qc failed",
        "model failed",
        "modelling failed",
        "reporting failed",
        "decomposition failed",
        "preprocessing failed",
        "alignment failed",
    )
    if any(term in text for term in analysis_terms):
        return _GUIDANCE["analysis"]

    return _GUIDANCE["unknown"]


def _detail_text(error: Any) -> str:
    detail = str(error).strip() or error.__class__.__name__
    if len(detail) > 220:
        detail = f"{detail[:217]}..."
    return detail


def format_failure(
    prefix: str,
    error: Any,
    *,
    public_safe: bool | None = None,
    context: str = "",
) -> str:
    """Format a caught failure for a Studio status surface.

    Local/private mode preserves the current concise exception detail and adds a
    stable recovery code. Public-safe mode never echoes the exception detail.
    Scientific exceptions are not modified or swallowed by this helper; callers
    invoke it only after their existing UI-boundary catch has already occurred.
    """

    detail = _detail_text(error)
    guidance = classify_failure(detail, context=f"{context} {prefix}")
    if public_safe is None:
        public_safe = studio_runtime_config().sanitize_errors

    recovery = f"[{guidance.code}] {guidance.title} Next: {guidance.next_action}"
    if public_safe:
        return f"{prefix}. {recovery}"
    return f"{prefix}: {detail} {recovery}"


def recovery_guidance(message: str, *, context: str = "") -> str:
    """Return privacy-safe recovery guidance for an existing failure/status text."""

    guidance = classify_failure(message, context=context)
    return f"[{guidance.code}] {guidance.title} Next: {guidance.next_action}"
