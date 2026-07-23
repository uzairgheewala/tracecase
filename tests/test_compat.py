from tracecase_bundle import BundleReader
from tracecase_compat import BundleHealthScanner, CaseQueryIndex, CompatibilityEngine
from tracecase_graph import GraphAssembler

def test_compatibility_and_health(generated_bundle):
    reader=BundleReader(generated_bundle)
    assessment=CompatibilityEngine().assess(reader)
    assert assessment.status.value=="compatible"
    health=BundleHealthScanner().scan(reader)
    assert health.valid and health.record_counts["model/nodes.jsonl"] > 0

def test_legacy_manifest_migration_plan():
    engine=CompatibilityEngine(); plan=engine.plan("0.9.0")
    assert plan.executable and plan.steps
    migrated=engine.migrate_manifest({"format_version":"0.9.0","bundle_id":"b"})
    assert migrated["format_version"]=="1.0.0" and "collection" in migrated

def test_query_index_neighborhood(generated_bundle):
    reader=BundleReader(generated_bundle); case=reader.load_case(); graph=GraphAssembler().assemble(case.evidence.execution)
    index=CaseQueryIndex(case,graph); center=graph.nodes[0].node_id
    neighborhood=index.neighborhood(center,depth=2)
    assert center in neighborhood.node_refs and index.summary().node_count==len(graph.nodes)

def test_streaming_page_and_archive_limits(generated_bundle, tmp_path):
    from tracecase_bundle import ArchiveLimits, BundleBuilder
    import zipfile
    reader=BundleReader(generated_bundle)
    first=reader.read_jsonl_page("model/nodes.jsonl",offset=0,limit=1)
    assert len(first)==1
    archive=tmp_path/"many.zip"
    with zipfile.ZipFile(archive,"w") as handle:
        handle.writestr("a.json","{}")
        handle.writestr("b.json","{}")
    try:
        BundleBuilder.unpack(archive,tmp_path/"out",limits=ArchiveLimits(max_entries=1))
    except ValueError as exc:
        assert "entries" in str(exc)
    else:
        raise AssertionError("archive entry limit was not enforced")
