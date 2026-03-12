"""Primary session API for structured TLAForge conversations."""

from __future__ import annotations

from pydantic import Field

from .compiler import DraftCompiler
from .draft import (
    ConversationMessage,
    DraftPatch,
    HandoffArtifact,
    MachineDraft,
    SessionTurnResult,
    StrictModel,
    ValidationResult,
)
from .errors import DraftNotReadyError
from .llm import StructuredTurnClient
from .patches import apply_patch_to_draft
from .validation import DraftValidator


class TLAForgeSession(StrictModel):
    """An in-memory conversation session for building a machine draft."""

    draft: MachineDraft = Field(default_factory=MachineDraft)
    transcript: list[ConversationMessage] = Field(default_factory=list)

    @classmethod
    def new(
        cls,
        *,
        module_name: str | None = None,
        summary: str | None = None,
    ) -> TLAForgeSession:
        return cls(draft=MachineDraft(module_name=module_name, summary=summary))

    def handle_user_message(
        self,
        message: str,
        client: StructuredTurnClient,
    ) -> SessionTurnResult:
        turn = client.complete_turn(
            draft=self.draft.model_copy(deep=True),
            transcript=list(self.transcript),
            user_message=message,
        )
        validation = self.apply_patch(turn.patch)
        self.transcript.append(ConversationMessage(role="user", content=message))
        self.transcript.append(ConversationMessage(role="assistant", content=turn.reply))
        return SessionTurnResult(
            reply=turn.reply,
            patch=turn.patch,
            draft=self.draft.model_copy(deep=True),
            validation=validation,
            ready_for_handoff=validation.ready,
        )

    def apply_patch(self, patch: DraftPatch) -> ValidationResult:
        updated_draft, patch_issues = apply_patch_to_draft(self.draft, patch)
        if patch_issues:
            return ValidationResult.from_issues(patch_issues)
        validation = DraftValidator.validate(updated_draft)
        self.draft = updated_draft
        return validation

    def validate(self) -> ValidationResult:
        return DraftValidator.validate(self.draft)

    def compile(self):
        return DraftCompiler().compile(self.draft)

    def export_handoff(self) -> HandoffArtifact:
        validation = self.validate()
        if not validation.ready:
            raise DraftNotReadyError(validation)
        tla_source = DraftCompiler().emit(self.draft)
        assert self.draft.module_name is not None
        return HandoffArtifact(
            module_name=self.draft.module_name,
            tla_source=tla_source,
            summary=self.draft.summary,
            assumptions=list(self.draft.assumptions),
            open_questions=[question.model_copy(deep=True) for question in self.draft.open_questions],
            validation=validation,
        )

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, payload: str) -> TLAForgeSession:
        return cls.model_validate_json(payload)
