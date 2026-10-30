"""Python side of the API → pipeline job contract (contracts/job.schema.json)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobType(StrEnum):
    DOCUMENT_PROCESS = "document.process"
    AUDIT_RUN = "audit.run"


class JobMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    job_id: UUID
    type: JobType
    condominium_id: int = Field(ge=1)
    correlation_id: str = Field(min_length=8, max_length=64)
    enqueued_at: datetime
    attempt: int = Field(ge=0)
    payload: dict[str, Any]

    def next_attempt(self) -> JobMessage:
        return self.model_copy(update={"attempt": self.attempt + 1})

    def to_json(self) -> str:
        return self.model_dump_json()
