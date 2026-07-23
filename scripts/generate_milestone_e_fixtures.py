from __future__ import annotations
import json, shutil
from pathlib import Path
from tracecase_analyzers import AnalyzerEngine
from tracecase_bundle import BundleBuilder, BundleProfile, PrivacyDescriptor, ProducerDescriptor, SupplementalArtifact
from tracecase_compat import BundleHealthScanner, CaseQueryIndex, CompatibilityEngine
from tracecase_coverage import CoverageEngine, MutationAdequacyEngine, MutationTrial, ScenarioMinimizer
from tracecase_graph import GraphAssembler
from tracecase_model import CaseCategory
from tracecase_pathforge import PathforgeTraceBridge, pathforge_bindings
from tracecase_scenarios import FaultApplication, FaultTargetKind, ScenarioDefinition, ScenarioGenerator, build_default_registry

ROOT=Path(__file__).resolve().parents[1]; BUNDLE_ROOT=ROOT/"fixtures"/"bundles"; REGISTRY_ROOT=ROOT/"registries"; PRODUCER=ProducerDescriptor(name="tracecase-milestone-e",version="0.5.0")

def clean(stem):
    d=BUNDLE_ROOT/f"{stem}.tracecase"; z=BUNDLE_ROOT/f"{stem}.tracecase.zip"
    if d.exists(): shutil.rmtree(d)
    if z.exists(): z.unlink()
    return d,z

def scenario_suite():
    registry=build_default_registry(); gen=ScenarioGenerator(registry); instances=[]
    for index,family in enumerate(registry.families):
        definition=ScenarioDefinition(scenario_id=f"scenario.coverage.{index}",title=family.title,family_ref=family.family_id)
        instances.append(gen.resolve(definition,seed=700+index))
        if family.allowed_fault_operator_refs:
            app=FaultApplication(application_id=f"application.coverage.{index}",operator_ref=family.allowed_fault_operator_refs[0],target_kind=FaultTargetKind.SYSTEM)
            instances.append(gen.resolve(definition.model_copy(update={"faults":(app,)}),seed=800+index))
    return registry,tuple(instances)

def build_pathforge(stem,case,extra=(),profiles=(BundleProfile.EVIDENCE,BundleProfile.ANALYZED,BundleProfile.REPRODUCIBLE,BundleProfile.PATHFORGE)):
    graph=GraphAssembler().assemble(case.evidence.execution); analysis=AnalyzerEngine().analyze(case,graph); timeline=GraphAssembler().timeline(graph,case.system)
    supplements=(SupplementalArtifact("analysis/assembled_graph.json",graph),SupplementalArtifact("analysis/timeline.json",timeline),SupplementalArtifact("analysis/invariant_results.json",analysis.invariant_report),SupplementalArtifact("analysis/findings.jsonl",analysis.findings,json_lines=True),SupplementalArtifact("analysis/analysis_report.json",analysis),*extra)
    d,z=clean(stem); builder=BundleBuilder(d,producer=PRODUCER); builder.build(case,overwrite=True,supplements=supplements,profiles=profiles,analysis_status="complete",privacy=PrivacyDescriptor(classification="internal")); builder.pack(z,overwrite=True); return d,z,graph,analysis

def main():
    BUNDLE_ROOT.mkdir(parents=True,exist_ok=True)
    bridge=PathforgeTraceBridge(); baseline=bridge.demo_case(seed=501); failure=bridge.demo_case(seed=501,fault="tenant-loss")
    base=build_pathforge("pathforge-audit-baseline",baseline,(SupplementalArtifact("pathforge/binding.json",bridge.binding),))
    fail=build_pathforge("pathforge-audit-context-loss",failure,(SupplementalArtifact("pathforge/binding.json",bridge.binding),))
    comparison=bridge.compare_demo(seed=501,fault="tenant-loss")[2]
    spec=failure.specification.model_copy(update={"case_id":"case.pathforge.audit.comparison","title":"Pathforge audit semantic comparison","category":CaseCategory.COMPARISON,"baseline_case_refs":(baseline.specification.case_id,failure.specification.case_id)})
    compcase=failure.model_copy(update={"specification":spec})
    build_pathforge("pathforge-audit-comparison",compcase,(SupplementalArtifact("pathforge/binding.json",bridge.binding),SupplementalArtifact("comparison/semantic_comparison.json",comparison),SupplementalArtifact("comparison/alignments.jsonl",comparison.alignments,json_lines=True),SupplementalArtifact("comparison/divergences.jsonl",comparison.divergences,json_lines=True)),profiles=(BundleProfile.EVIDENCE,BundleProfile.ANALYZED,BundleProfile.REPRODUCIBLE,BundleProfile.PATHFORGE,BundleProfile.COMPARISON))
    registry,instances=scenario_suite(); coverage=CoverageEngine(registry).evaluate(instances,realizations={item.instance_id:("pathforge" if item.family_ref.startswith("continuity") else "synthetic") for item in instances})
    essential=FaultApplication(application_id="essential",operator_ref="fault.context.drop.v1",target_kind=FaultTargetKind.SYSTEM); extra=FaultApplication(application_id="extra",operator_ref="fault.observability.break-link.v1",target_kind=FaultTargetKind.SYSTEM)
    definition=ScenarioDefinition(scenario_id="scenario.coverage.minimize",title="Coverage minimization witness",family_ref="continuity.context_disappearance.v1",parameter_bindings={"irrelevant":True},faults=(essential,extra))
    minimized,min_report=ScenarioMinimizer().minimize_definition(definition,target_ref="context.required_continuity.v1",preserves=lambda item:any(f.operator_ref=="fault.context.drop.v1" for f in item.faults))
    mutation=MutationAdequacyEngine().evaluate((MutationTrial(trial_id="mutation.context",mutation_ref="drop-context",target_ref="context.required_continuity.v1",detected=True,actual_changes=("context.required_continuity.v1",)),MutationTrial(trial_id="mutation.effect",mutation_ref="duplicate-effect",target_ref="effect.at_most_once.v1",detected=True,actual_changes=("effect.at_most_once.v1",))))
    reader_path=base[0]
    from tracecase_bundle import BundleReader
    reader=BundleReader(reader_path); compatibility=CompatibilityEngine().assess(reader); health=BundleHealthScanner().scan(reader); query=CaseQueryIndex(baseline,base[2])
    carrier=bridge.demo_case(seed=502)
    build_pathforge("tracecase-coverage-and-health",carrier,(SupplementalArtifact("coverage/ledger.json",coverage),SupplementalArtifact("coverage/minimized_definition.json",minimized),SupplementalArtifact("coverage/minimization_report.json",min_report),SupplementalArtifact("coverage/mutation_adequacy.json",mutation),SupplementalArtifact("compatibility/assessment.json",compatibility),SupplementalArtifact("compatibility/health_report.json",health),SupplementalArtifact("compatibility/query_index_summary.json",query.summary())),profiles=(BundleProfile.EVIDENCE,BundleProfile.ANALYZED,BundleProfile.REPRODUCIBLE,BundleProfile.COVERAGE))
    (REGISTRY_ROOT/"pathforge").mkdir(parents=True,exist_ok=True); (REGISTRY_ROOT/"pathforge"/"bindings.json").write_text(json.dumps([v.model_dump(mode="json") for v in pathforge_bindings()],indent=2,sort_keys=True)+"\n")
    (REGISTRY_ROOT/"coverage").mkdir(parents=True,exist_ok=True); (REGISTRY_ROOT/"coverage"/"dimensions.json").write_text(json.dumps({"dimensions":["family","universe_axis","topology","fault_operator","invariant","observability","interaction","outcome","realization"]},indent=2)+"\n")
    for stem in ("pathforge-audit-baseline","pathforge-audit-context-loss","pathforge-audit-comparison","tracecase-coverage-and-health"): print("Generated",stem)
if __name__=="__main__": main()
