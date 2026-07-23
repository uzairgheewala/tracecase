from __future__ import annotations
from datetime import datetime, timedelta, timezone
from tracecase_analyzers import AnalyzerEngine
from tracecase_compare import SemanticComparisonEngine
from tracecase_graph import GraphAssembler
from tracecase_invariants import InvariantRuntime
from tracecase_model import *
from tracecase_model.execution import EffectDurability
from tracecase_sdk import InMemorySink, SDKContext, SDKEvent, SDKEventKind, TracecaseSDK
from .models import PathforgeDomainEvent, PathforgeRunContext, PathforgeRunResult
from .registry import get_binding

class PathforgeTraceBridge:
    def __init__(self,binding_id="pathforge.requirement-audit.v1"): self.binding=get_binding(binding_id)
    @staticmethod
    def deep_link(case_id:str,*,node_id:str|None=None,finding_id:str|None=None,base_url:str="/tracecase"):
        value=f"{base_url}/cases/{case_id}"
        query=[]
        if node_id: query.append(f"node={node_id}")
        if finding_id: query.append(f"finding={finding_id}")
        return value+("?"+"&".join(query) if query else "")

    def demo_case(self,*,seed:int=1,fault:str|None=None)->ExecutionCase:
        start=datetime(2026,7,23,20,0,tzinfo=timezone.utc)+timedelta(seconds=seed)
        tenant="institution-alpha"
        operations=[
            ("request","audit.requested",NodeKind.REQUEST_HANDLER,"pathforge-api",0),
            ("candidates","audit.candidates.generated",NodeKind.DOMAIN_OPERATION,"reqgraph",35),
            ("solver","audit.solver.completed",NodeKind.DOMAIN_OPERATION,"reqgraph",90),
            ("explanation","audit.explanation.generated",NodeKind.DOMAIN_OPERATION,"reqgraph",145),
            ("persist","audit.persisted",NodeKind.WRITE,"postgres",200),
        ]
        if fault=="stale-audit": operations[-1]=(operations[-1][0],"audit.persisted.stale",NodeKind.WRITE,"postgres",200)
        components=tuple(Component(component_id=f"component.pathforge.{name}",name=name,kind=ComponentKind.SERVICE if name!="postgres" else ComponentKind.DATABASE,role=name) for name in {op[3] for op in operations})
        boundaries=tuple(Boundary(boundary_id=f"boundary.pathforge.{i}",name=f"stage {i}",kind=BoundaryKind.FUNCTION_CALL,source_component_ref=f"component.pathforge.{operations[i][3]}",target_component_ref=f"component.pathforge.{operations[i+1][3]}") for i in range(len(operations)-1))
        resource=Resource(resource_id="resource.pathforge.audit",kind="audit_result",name="Requirement audit result",owner_component_ref="component.pathforge.postgres",sensitivity={SensitivityLabel.STUDENT_RECORD})
        source=SourceDescriptor(source_id="source.pathforge",source_kind="pathforge_domain_events",name="Pathforge domain event stream",captured_at=start+timedelta(seconds=1))
        nodes=[]; observations=[]; contexts=[]; relations=[]
        for i,(role,operation,kind,component,offset) in enumerate(operations):
            node_id=f"node.pathforge.{role}"; obs_id=f"observation.pathforge.{role}"
            tenant_value=None if fault=="tenant-loss" and role in {"solver","explanation","persist"} else tenant
            ids=ExecutionIdentitySet(trace_id=f"trace-pathforge-{seed}",workflow_id=f"workflow-pathforge-{seed}",logical_operation_id=f"audit-{seed}",tenant_id=tenant_value)
            context_refs=()
            if tenant_value:
                ctx=f"context.pathforge.tenant.{role}"; contexts.append(ContextField(context_id=ctx,namespace="tenant",field_name="tenant_id",value=tenant_value,propagation_contract=PropagationContract.REQUIRED,origin_node_ref="node.pathforge.request",observed_at_node_ref=node_id,sensitivity={SensitivityLabel.TENANT_IDENTIFIER},extensions={"pathforge.academic":{"engagement_id":f"engagement-{seed}"},"tracecase.scenario":{"contract_ref":"tenant-continuity","required_role_refs":["request","candidates","solver","explanation","persist"]}})); context_refs=(ctx,)
            observations.append(Observation(observation_id=obs_id,kind=ObservationKind.DOMAIN_EVENT,provenance=ProvenanceRef(source_id=source.source_id,source_native_id=role),captured_at=start+timedelta(seconds=1),event_time=TimeObservation(raw_timestamp=start+timedelta(milliseconds=offset),normalized_timestamp=start+timedelta(milliseconds=offset),clock_ref=f"clock.{component}",precision_ns=1_000_000),normalized_refs=(node_id,),attributes={"event_type":operation,"catalog_version":"2026.1"},sensitivity={SensitivityLabel.INTERNAL}))
            nodes.append(ExecutionNode(node_id=node_id,kind=kind,operation=operation,component_ref=f"component.pathforge.{component}",boundary_refs=(() if i==0 else (f"boundary.pathforge.{i-1}",)),identities=ids,context_refs=context_refs,timing=TimeObservation(raw_timestamp=start+timedelta(milliseconds=offset),normalized_timestamp=start+timedelta(milliseconds=offset),clock_ref=f"clock.{component}",precision_ns=1_000_000),end_time=TimeObservation(raw_timestamp=start+timedelta(milliseconds=offset+20),normalized_timestamp=start+timedelta(milliseconds=offset+20),clock_ref=f"clock.{component}",precision_ns=1_000_000),status="ok",observation_refs=(obs_id,),attributes={"scenario_role_ref":role,"pathforge_stage":role},extensions={"pathforge.academic":{"catalog_version":"2026.1","audit_run_id":f"audit-{seed}"}}))
            if i: relations.append(ExecutionRelation(relation_id=f"relation.pathforge.{i}",kind=RelationKind.INVOKES,source_ref=nodes[i-1].node_id,target_ref=node_id,derivation=DerivationKind.EXPLICIT,evidence_refs=(observations[i-1].observation_id,obs_id)))
        effect=Effect(effect_id="effect.pathforge.audit",kind=EffectKind.STATE_UPDATE,logical_effect_key=f"audit-result/{seed}",producer_node_ref="node.pathforge.persist",target_resource_ref=resource.resource_id,operation="persist requirement audit",idempotency_key=f"audit-{seed}",durability=EffectDurability.DURABLE,completion_status="completed",evidence_refs=("observation.pathforge.persist",),sensitivity={SensitivityLabel.STUDENT_RECORD},attributes={"required":True,"maximum_durable_count":1,"catalog_version":"2025.9" if fault=="stale-audit" else "2026.1"})
        nodes[-1]=nodes[-1].model_copy(update={"effect_refs": (effect.effect_id,)})
        execution=ExecutionModel(execution_id=f"execution.pathforge.{seed}.{fault or 'baseline'}",nodes=tuple(nodes),relations=tuple(relations),contexts=tuple(contexts),effects=(effect,),observations=tuple(observations),evidence_classification=EvidenceClassification.RECORDED,extensions={"pathforge.academic":{"binding_ref":self.binding.binding_id,"catalog_version":"2026.1","expected_effects":[{"logical_effect_key":effect.logical_effect_key,"required":True}]}})
        return ExecutionCase(specification=CaseSpecification(case_id=f"case.pathforge.{seed}.{fault or 'baseline'}",title=f"Pathforge requirement audit: {fault or 'baseline'}",category=CaseCategory.HYBRID,created_at=start,roots=({"kind":"workflow_id","value":f"workflow-pathforge-{seed}"},),scenario_ref=self.binding.binding_id,description="Pathforge domain integration expressed through generic Tracecase execution semantics."),system=SystemModel(system_id="system.pathforge",name="Pathforge",components=components,boundaries=boundaries,resources=(resource,),extensions={"pathforge.academic":{"integration_version":"1.0.0"}}),evidence=CaseEvidence(sources=(source,),execution=execution),interpretations=CaseInterpretations(),lifecycle=LifecycleStatus.COLLECTED,extensions={"pathforge.academic":{"binding_ref":self.binding.binding_id}})

    def analyze(self,case:ExecutionCase)->PathforgeRunResult:
        graph=GraphAssembler().assemble(case.evidence.execution); analysis=AnalyzerEngine().analyze(case,graph)
        return PathforgeRunResult(binding=self.binding,case_id=case.specification.case_id,graph_id=graph.graph_id,invariant_summary={str(k):v for k,v in analysis.invariant_report.summary.items()},finding_count=len(analysis.findings),deep_link=self.deep_link(case.specification.case_id),attributes={"node_count":len(graph.nodes),"effect_count":len(graph.effect_groups)})

    def compare_demo(self,*,seed:int=1,fault:str="tenant-loss"):
        baseline=self.demo_case(seed=seed); candidate=self.demo_case(seed=seed,fault=fault)
        bg=GraphAssembler().assemble(baseline.evidence.execution); cg=GraphAssembler().assemble(candidate.evidence.execution)
        return baseline,candidate,SemanticComparisonEngine().compare(baseline,bg,candidate,cg)
