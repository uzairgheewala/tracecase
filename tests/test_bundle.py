from pathlib import Path

from tracecase_bundle import BundleBuilder, BundleReader


def test_bundle_round_trip(generated_bundle: Path) -> None:
    reader = BundleReader(generated_bundle)
    result = reader.verify()
    assert result.valid
    case = reader.load_case()
    assert case.specification.case_id == "case.minimal-success"
    assert len(case.evidence.execution.nodes) == 6
    assert len(case.evidence.execution.effects) == 1


def test_tampering_is_detected(generated_bundle: Path) -> None:
    path = generated_bundle / "model" / "nodes.jsonl"
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    result = BundleReader(generated_bundle).verify()
    assert not result.valid
    assert "model/nodes.jsonl" in result.mismatched_paths


def test_pack_unpack_round_trip(generated_bundle: Path, tmp_path: Path) -> None:
    builder = BundleBuilder(generated_bundle)
    builder._frozen = True  # Existing verified fixture; pack does not mutate it.
    archive = builder.pack(tmp_path / "case.tracecase.zip")
    unpacked = BundleBuilder.unpack(archive, tmp_path / "unpacked")
    assert BundleReader(unpacked).verify().valid
