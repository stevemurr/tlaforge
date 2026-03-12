"""Shared exceptions for TLAForge runtime layers."""

from __future__ import annotations

from .draft import ValidationResult


class TLAForgeError(Exception):
    """Base class for TLAForge failures."""


class DraftNotReadyError(TLAForgeError):
    """Raised when compile/export is requested before the draft is ready."""

    def __init__(self, validation: ValidationResult):
        super().__init__("Draft is not ready for handoff")
        self.validation = validation


class StructuredOutputError(TLAForgeError):
    """Raised when an LLM response cannot be parsed into the required schema."""
