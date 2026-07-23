from pathlib import Path

from tracecase_bundle import BundleBuilder, BundleReader
from tracecase_lab import LabRunRequest, ReferenceLab
from tracecase_policy import (
    ExportValidator,
    PolicyEngine,
    ShareableBundleExporter,
    default_internal_policy,
    default_shareable_policy,
)


def test_shareable_policy_tokenizes_and_removes_credentials() -> None:
    case = ReferenceLab().run(
        LabRunRequest(
            seed=31,
            fault_operator_ref="fault.privacy.capture-secret.v1",
            include_sensitive_payload=True,
        )
    ).case
    engine = PolicyEngine(default_shareable_policy(), token_key=b"test-key")
    sanitized, report = engine.apply(case)
    payload = sanitized.model_dump_json()
    assert report.valid_for_export
    assert "very-secret-production-token" not in payload
    assert "uzair.student@example.edu" not in payload
    assert report.token_count > 0
    assert any(item.action.value == "remove" for item in report.transformations)
    assert ExportValidator().validate_case(sanitized, default_shareable_policy()).valid


def test_tokenization_is_stable_and_reference_safe() -> None:
    case = ReferenceLab().run(LabRunRequest(seed=32)).case
    first, first_report = PolicyEngine(default_shareable_policy(), token_key=b"stable").apply(case)
    second, second_report = PolicyEngine(default_shareable_policy(), token_key=b"stable").apply(case)
    assert first.evidence.execution.nodes[0].identities.tenant_id == second.evidence.execution.nodes[0].identities.tenant_id
    assert first_report.output_digest == second_report.output_digest
    assert first.evidence.execution.nodes[0].node_id == case.evidence.execution.nodes[0].node_id


def test_internal_policy_rejects_credential_capture() -> None:
    case = ReferenceLab().run(
        LabRunRequest(seed=33, fault_operator_ref="fault.privacy.capture-secret.v1", include_sensitive_payload=True)
    ).case
    _, report = PolicyEngine(default_internal_policy()).apply(case)
    assert not report.valid_for_export
    assert any(item.code == "policy_reject" for item in report.violations)


def test_shareable_export_is_integrity_valid(tmp_path: Path) -> None:
    case = ReferenceLab().run(
        LabRunRequest(seed=34, fault_operator_ref="fault.privacy.capture-secret.v1", include_sensitive_payload=True)
    ).case
    source = tmp_path / "source.tracecase"
    builder = BundleBuilder(source)
    builder.build(case)
    reader = BundleReader(source)
    result = ShareableBundleExporter(default_shareable_policy(), token_key=b"export-key").export(
        reader,
        tmp_path / "shareable.tracecase",
        archive_path=tmp_path / "shareable.tracecase.zip",
    )
    assert result.validation_report.valid
    exported = BundleReader(Path(result.bundle_path))
    assert exported.verify().valid
    assert exported.manifest.privacy.classification == "shareable"
    assert exported.has_artifact("policy/redaction_report.json")
    zipped, temporary = BundleReader.open(Path(result.archive_path or ""))
    try:
        assert zipped.verify().valid
    finally:
        if temporary:
            temporary.cleanup()
