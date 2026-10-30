"""The Python model and the shared JSON Schema must agree (the PHP suite runs
the same schema against what the API publishes)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from condo_audit.jobs import JobMessage, JobType
from tests.conftest import make_message


@pytest.fixture
def validator(contracts_dir: Path) -> Draft202012Validator:
    schema = json.loads((contracts_dir / "job.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


@pytest.mark.parametrize("job_type", list(JobType))
def test_serialized_messages_match_the_schema(validator: Draft202012Validator, job_type: JobType) -> None:
    validator.validate(json.loads(make_message(job_type).to_json()))


def test_schema_rejects_a_document_job_without_document_id(validator: Draft202012Validator) -> None:
    payload = json.loads(make_message(JobType.DOCUMENT_PROCESS, payload={}).to_json())
    assert not validator.is_valid(payload)


def test_model_rejects_unknown_fields_and_versions() -> None:
    raw = json.loads(make_message().to_json())
    with pytest.raises(ValidationError):
        JobMessage.model_validate({**raw, "unexpected": True})
    with pytest.raises(ValidationError):
        JobMessage.model_validate({**raw, "schema_version": 2})


def test_message_published_by_the_api_is_accepted() -> None:
    # Exact shape produced by App\Pipeline\JobMessage::toJson() in the API.
    raw = (
        '{"schema_version":1,"job_id":"0b9a2c3e-6f4d-4b0a-9c1e-2d3f4a5b6c7d","type":"audit.run",'
        '"condominium_id":3,"correlation_id":"01jbx7q2v9k8w3m4n5p6r7s8t9","enqueued_at":"2026-01-15T10:20:30.123+00:00",'
        '"attempt":0,"payload":{}}'
    )
    message = JobMessage.model_validate_json(raw)
    assert message.type is JobType.AUDIT_RUN
    assert message.payload == {}
