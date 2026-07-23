import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  compareCases,
  generateScenario,
  getAnalysis,
  getAssembledGraph,
  getCase,
  getTimeline,
  getValidation,
  listCases,
  listScenarioFamilies,
} from "./api";
import type {
  AnalysisReport,
  AssembledGraph,
  CaseDetail,
  CaseSummary,
  Divergence,
  Finding,
  GeneratedScenario,
  GraphNode,
  ScenarioFamily,
  SemanticComparison,
  SystemModel,
  TimelineModel,
} from "./types";

type WorkspaceMode = "explore" | "construct" | "compare";
type VisualMode = "graph" | "timeline" | "semantics";

function Metric({ label, value, detail }: { label: string; value: number | string; detail?: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function GraphCanvas({
  graph,
  system,
  selectedNodeId,
  onSelect,
}: {
  graph: AssembledGraph;
  system: SystemModel;
  selectedNodeId?: string;
  onSelect: (nodeId: string) => void;
}) {
  const width = 1120;
  const laneHeight = 132;
  const labelWidth = 170;
  const nodeWidth = 150;
  const nodeHeight = 56;
  const components = system.components.length
    ? system.components
    : Array.from(new Set(graph.nodes.map((node) => node.component_ref))).map((componentId) => ({
        component_id: componentId,
        name: componentId,
        kind: "unknown",
      }));
  const laneByComponent = new Map(components.map((component, index) => [component.component_id, index]));
  const starts = graph.nodes.map((node) => Date.parse(node.timing.normalized_timestamp ?? node.timing.raw_timestamp));
  const min = Math.min(...starts);
  const max = Math.max(...starts);
  const range = Math.max(max - min, 1);
  const positions = new Map<string, { x: number; y: number }>();
  graph.nodes.forEach((node, index) => {
    const start = Date.parse(node.timing.normalized_timestamp ?? node.timing.raw_timestamp);
    const ratio = (start - min) / range;
    const lane = laneByComponent.get(node.component_ref) ?? index % Math.max(components.length, 1);
    const x = labelWidth + 30 + ratio * (width - labelWidth - nodeWidth - 70);
    const y = lane * laneHeight + 42;
    positions.set(node.node_id, { x, y });
  });
  const warningNodes = new Set(graph.report.warnings.flatMap((warning) => warning.node_refs));
  const height = Math.max(components.length * laneHeight + 24, 220);

  return (
    <div className="graph-scroll" aria-label="Assembled execution graph">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Execution nodes arranged by component and time">
        <defs>
          <marker id="arrow-explicit" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="arrow-explicit" />
          </marker>
          <marker id="arrow-derived" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="arrow-derived" />
          </marker>
        </defs>
        {components.map((component, index) => (
          <g key={component.component_id}>
            <line x1={labelWidth} x2={width - 20} y1={index * laneHeight + 70} y2={index * laneHeight + 70} className="lane-line" />
            <text x="12" y={index * laneHeight + 58} className="lane-title">{component.name}</text>
            <text x="12" y={index * laneHeight + 78} className="lane-subtitle">{component.kind.replaceAll("_", " ")}</text>
          </g>
        ))}
        {graph.relations.map((relation) => {
          const source = positions.get(relation.source_ref);
          const target = positions.get(relation.target_ref);
          if (!source || !target) return null;
          const x1 = source.x + nodeWidth;
          const y1 = source.y + nodeHeight / 2;
          const x2 = target.x;
          const y2 = target.y + nodeHeight / 2;
          const middle = Math.max(24, Math.abs(x2 - x1) / 2);
          const path = `M ${x1} ${y1} C ${x1 + middle} ${y1}, ${x2 - middle} ${y2}, ${x2} ${y2}`;
          const derived = relation.derivation === "deterministic" || relation.derivation === "heuristic";
          return (
            <g key={relation.relation_id}>
              <path
                d={path}
                className={`graph-edge edge-${relation.derivation}`}
                markerEnd={`url(#arrow-${derived ? "derived" : "explicit"})`}
              />
              <title>{`${relation.kind} · ${relation.derivation}`}</title>
            </g>
          );
        })}
        {graph.nodes.map((node) => {
          const position = positions.get(node.node_id)!;
          const selected = node.node_id === selectedNodeId;
          const warned = warningNodes.has(node.node_id);
          return (
            <g
              key={node.node_id}
              role="button"
              aria-label={`${node.operation}, ${node.status}`}
              className="graph-node-group"
              onClick={() => onSelect(node.node_id)}
            >
              <rect
                x={position.x}
                y={position.y}
                width={nodeWidth}
                height={nodeHeight}
                rx="9"
                className={`graph-node ${selected ? "selected" : ""} ${warned ? "warned" : ""}`}
              />
              <text x={position.x + 10} y={position.y + 18} className="node-kind-label">
                {node.kind.replaceAll("_", " ").slice(0, 22)}
              </text>
              <text x={position.x + 10} y={position.y + 37} className="node-operation-label">
                {node.operation.length > 22 ? `${node.operation.slice(0, 20)}…` : node.operation}
              </text>
              <text x={position.x + 10} y={position.y + 50} className={`node-status-label status-${node.status}`}>
                {node.identities.task_attempt ? `attempt ${String(node.identities.task_attempt)} · ` : ""}{node.status}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function TimelineView({ timeline, selectedNodeId, onSelect }: { timeline: TimelineModel; selectedNodeId?: string; onSelect: (id: string) => void }) {
  const total = Math.max(timeline.total_duration_ms, 1);
  return (
    <div className="timeline" aria-label="Execution timeline">
      <div className="timeline-axis">
        <span>0 ms</span><span>{Math.round(total / 2)} ms</span><span>{Math.round(total)} ms</span>
      </div>
      {timeline.lanes.map((lane) => (
        <div className="timeline-lane" key={lane.lane_id}>
          <div className="timeline-label"><strong>{lane.label}</strong><small>{lane.component_ref}</small></div>
          <div className="timeline-track">
            {lane.entries.map((entry) => {
              const left = (entry.start_offset_ms / total) * 100;
              const width = Math.max((Math.max(entry.duration_ms, 4) / total) * 100, 1.4);
              return (
                <button
                  type="button"
                  key={entry.entry_id}
                  className={`timeline-entry ${selectedNodeId === entry.node_ref ? "selected" : ""}`}
                  style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                  onClick={() => onSelect(entry.node_ref)}
                  title={`${entry.operation} · ${entry.start_offset_ms.toFixed(1)} ms · ${entry.duration_ms.toFixed(1)} ms`}
                >
                  <span>{entry.operation}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function SemanticsView({ graph }: { graph: AssembledGraph }) {
  return (
    <div className="semantic-grid">
      <section className="semantic-panel">
        <div className="section-heading"><div><span className="eyebrow">Identity</span><h3>Correlation groups</h3></div><Badge>{graph.identity_groups.length}</Badge></div>
        {graph.identity_groups.length ? graph.identity_groups.map((group) => (
          <div className="semantic-row" key={group.group_id}>
            <div><strong>{group.kind.replaceAll("_", " ")}</strong><code>{group.identity_value}</code></div>
            <span>{group.member_node_refs.length} nodes</span>
          </div>
        )) : <p className="muted">No multi-node identity groups.</p>}
      </section>
      <section className="semantic-panel">
        <div className="section-heading"><div><span className="eyebrow">Context</span><h3>Propagation flows</h3></div><Badge>{graph.context_flows.length}</Badge></div>
        {graph.context_flows.length ? graph.context_flows.map((flow) => (
          <div className="semantic-row" key={flow.flow_id}>
            <div><strong>{flow.qualified_name}</strong><code>{flow.source_node_ref} → {flow.target_node_ref}</code></div>
            <Badge tone={flow.status === "preserved" ? "good" : "warning"}>{flow.status}</Badge>
          </div>
        )) : <p className="muted">No reconstructable context flows.</p>}
      </section>
      <section className="semantic-panel">
        <div className="section-heading"><div><span className="eyebrow">Effects</span><h3>Logical effect groups</h3></div><Badge>{graph.effect_groups.length}</Badge></div>
        {graph.effect_groups.length ? graph.effect_groups.map((group) => (
          <div className="semantic-row" key={group.group_id}>
            <div><strong>{group.logical_effect_key}</strong><code>{group.member_effect_refs.join(", ")}</code></div>
            <Badge tone={group.durable_count > 1 ? "danger" : "good"}>{group.durable_count} durable</Badge>
          </div>
        )) : <p className="muted">No effect groups.</p>}
      </section>
      <section className="semantic-panel">
        <div className="section-heading"><div><span className="eyebrow">Integrity</span><h3>Assembly warnings</h3></div><Badge tone={graph.report.warnings.length ? "warning" : "good"}>{graph.report.warnings.length}</Badge></div>
        {graph.report.warnings.length ? graph.report.warnings.map((warning) => (
          <div className="warning-row" key={warning.warning_id}><strong>{warning.code.replaceAll("_", " ")}</strong><p>{warning.message}</p></div>
        )) : <p className="muted">No graph-assembly warnings.</p>}
      </section>
    </div>
  );
}

function NodeInspector({ node, graph }: { node?: GraphNode; graph?: AssembledGraph }) {
  if (!node || !graph) return <p className="muted">Select an execution node to inspect its identities, semantic links, and evidence references.</p>;
  const relations = graph.relations.filter((relation) => relation.source_ref === node.node_id || relation.target_ref === node.node_id);
  const groups = graph.identity_groups.filter((group) => group.member_node_refs.includes(node.node_id));
  const flows = graph.context_flows.filter((flow) => flow.source_node_ref === node.node_id || flow.target_node_ref === node.node_id);
  return (
    <div className="inspector-content">
      <div><span className="eyebrow">{node.kind.replaceAll("_", " ")}</span><h2>{node.operation}</h2><code>{node.node_id}</code></div>
      <dl>
        <dt>Component</dt><dd>{node.component_ref}</dd>
        <dt>Status</dt><dd>{node.status}</dd>
        <dt>Start</dt><dd>{node.timing.normalized_timestamp ?? node.timing.raw_timestamp}</dd>
        <dt>Context refs</dt><dd>{node.context_refs.length || "None"}</dd>
        <dt>Effect refs</dt><dd>{node.effect_refs.length || "None"}</dd>
        <dt>Evidence refs</dt><dd>{node.observation_refs.length || "None"}</dd>
      </dl>
      <section><h3>Identities</h3>{Object.entries(node.identities).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => <div className="key-value" key={key}><span>{key.replaceAll("_", " ")}</span><code>{String(value)}</code></div>)}</section>
      <section><h3>Identity groups</h3>{groups.length ? groups.map((group) => <div className="relation-row" key={group.group_id}><span>{group.kind.replaceAll("_", " ")}</span><small>{group.member_node_refs.length} members</small></div>) : <p className="muted">No shared groups.</p>}</section>
      <section><h3>Relationships</h3>{relations.map((relation) => <div className="relation-row" key={relation.relation_id}><span>{relation.kind.replaceAll("_", " ")}</span><small>{relation.derivation}</small></div>)}</section>
      <section><h3>Context flows</h3>{flows.length ? flows.map((flow) => <div className="relation-row" key={flow.flow_id}><span>{flow.qualified_name}</span><small>{flow.status}</small></div>) : <p className="muted">No flow touches this node.</p>}</section>
      <details><summary>Canonical JSON</summary><pre>{JSON.stringify(node, null, 2)}</pre></details>
    </div>
  );
}

function VisualSwitcher({ value, onChange }: { value: VisualMode; onChange: (value: VisualMode) => void }) {
  return (
    <div className="segmented" aria-label="Visualization mode">
      {(["graph", "timeline", "semantics"] as VisualMode[]).map((item) => (
        <button type="button" className={value === item ? "active" : ""} key={item} onClick={() => onChange(item)}>{item}</button>
      ))}
    </div>
  );
}

function severityTone(value: string): string {
  if (value === "critical" || value === "high" || value === "violated" || value === "contradicted") return "danger";
  if (value === "medium" || value === "inconclusive") return "warning";
  if (value === "satisfied") return "good";
  return "neutral";
}

function AnalysisPanels({
  analysis,
  selectedFindingId,
  onSelectFinding,
  onSelectNode,
}: {
  analysis?: AnalysisReport;
  selectedFindingId?: string;
  onSelectFinding: (id: string) => void;
  onSelectNode: (id: string) => void;
}) {
  if (!analysis) return <p className="muted">Loading invariant and analyzer results…</p>;
  return (
    <section className="analysis-grid">
      <div className="analysis-panel">
        <div className="section-heading"><div><span className="eyebrow">Invariant runtime</span><h2>Contract evaluation</h2></div><Badge>{analysis.invariant_report.results.length}</Badge></div>
        <div className="analysis-list">
          {analysis.invariant_report.results.map((result) => (
            <button type="button" className="analysis-row" key={result.result_id} onClick={() => result.node_refs[0] && onSelectNode(result.node_refs[0])}>
              <Badge tone={severityTone(result.status)}>{result.status}</Badge>
              <div><strong>{result.invariant_ref}</strong><p>{result.explanation}</p></div>
              <small>{Math.round(result.confidence.score * 100)}%</small>
            </button>
          ))}
        </div>
      </div>
      <div className="analysis-panel">
        <div className="section-heading"><div><span className="eyebrow">Bounded analyzers</span><h2>Evidence-linked findings</h2></div><Badge tone={analysis.findings.length ? "warning" : "good"}>{analysis.findings.length}</Badge></div>
        {analysis.findings.length ? <div className="analysis-list">{analysis.findings.map((finding) => (
          <button type="button" className={`analysis-row ${finding.finding_id === selectedFindingId ? "selected" : ""}`} key={finding.finding_id} onClick={() => { onSelectFinding(finding.finding_id); if (finding.node_refs[0]) onSelectNode(finding.node_refs[0]); }}>
            <Badge tone={severityTone(finding.severity)}>{finding.severity}</Badge>
            <div><strong>{finding.title}</strong><p>{finding.summary}</p></div>
            <small>{finding.evidence_classification}</small>
          </button>
        ))}</div> : <p className="muted">No bounded analyzer findings for this case.</p>}
      </div>
    </section>
  );
}

function FindingInspector({ finding }: { finding?: Finding }) {
  if (!finding) return null;
  return (
    <section className="finding-inspector">
      <span className="eyebrow">Selected finding</span>
      <h3>{finding.title}</h3>
      <Badge tone={severityTone(finding.severity)}>{finding.severity}</Badge>
      <p>{finding.summary}</p>
      <dl>
        <dt>Classification</dt><dd>{finding.classification}</dd>
        <dt>Evidence class</dt><dd>{finding.evidence_classification}</dd>
        <dt>Confidence</dt><dd>{Math.round(finding.confidence.score * 100)}%</dd>
        <dt>Evidence refs</dt><dd>{finding.evidence_refs.length}</dd>
      </dl>
      {finding.recommended_inspection_points.map((item) => <div className="inspection-point" key={item}>{item}</div>)}
      {finding.limitations.map((item) => <div className="limitation" key={item}>{item}</div>)}
    </section>
  );
}

function CaseWorkspace({
  detail,
  graph,
  timeline,
  selectedNodeId,
  onSelectNode,
  visualMode,
  onVisualMode,
  analysis,
  selectedFindingId,
  onSelectFinding,
}: {
  detail?: CaseDetail;
  graph?: AssembledGraph;
  timeline?: TimelineModel;
  selectedNodeId?: string;
  onSelectNode: (id: string) => void;
  visualMode: VisualMode;
  onVisualMode: (mode: VisualMode) => void;
  analysis?: AnalysisReport;
  selectedFindingId?: string;
  onSelectFinding: (id: string) => void;
}) {
  if (!detail || !graph || !timeline) return <p className="muted">Loading canonical evidence and derived graph…</p>;
  return (
    <>
      <div className="case-heading">
        <div><span className="eyebrow">{detail.specification.category.replaceAll("_", " ")}</span><h2>{detail.specification.title}</h2><p>{detail.specification.description}</p></div>
        <div className="heading-tags">
          {detail.manifest.scenario?.family_ref ? <Badge tone="accent">{detail.manifest.scenario.family_ref}</Badge> : null}
          {detail.ground_truth_available ? <Badge>Ground truth included</Badge> : null}
        </div>
      </div>
      <div className="metrics">
        <Metric label="Nodes" value={detail.summary.nodes ?? 0} />
        <Metric label="Relations" value={detail.summary.relations ?? 0} detail={`${detail.summary.derived_relations ?? 0} derived`} />
        <Metric label="Contexts" value={detail.summary.contexts ?? 0} detail={`${detail.summary.context_flows ?? 0} flows`} />
        <Metric label="Effects" value={detail.summary.effects ?? 0} detail={`${detail.summary.effect_groups ?? 0} groups`} />
        <Metric label="Warnings" value={detail.summary.warnings ?? 0} />
      </div>
      <section className="visual-section">
        <div className="section-heading">
          <div><span className="eyebrow">Milestone C</span><h2>Reconstructed and evaluated execution</h2></div>
          <VisualSwitcher value={visualMode} onChange={onVisualMode} />
        </div>
        {visualMode === "graph" ? <GraphCanvas graph={graph} system={detail.system} selectedNodeId={selectedNodeId} onSelect={onSelectNode} /> : null}
        {visualMode === "timeline" ? <TimelineView timeline={timeline} selectedNodeId={selectedNodeId} onSelect={onSelectNode} /> : null}
        {visualMode === "semantics" ? <SemanticsView graph={graph} /> : null}
      </section>
      <AnalysisPanels analysis={analysis} selectedFindingId={selectedFindingId} onSelectFinding={onSelectFinding} onSelectNode={onSelectNode} />
      {detail.oracle?.length ? (
        <section className="visual-section">
          <div className="section-heading"><div><span className="eyebrow">Synthetic oracle</span><h2>Expected invariant outcomes</h2></div><Badge>{detail.oracle.length}</Badge></div>
          <div className="oracle-grid">
            {detail.oracle.map((item) => <div className="oracle-card" key={item.invariant_ref}><Badge tone={item.expected_status === "satisfied" ? "good" : item.expected_status === "inconclusive" ? "warning" : "danger"}>{item.expected_status}</Badge><strong>{item.invariant_ref}</strong><p>{item.basis}</p></div>)}
          </div>
        </section>
      ) : null}
    </>
  );
}

function ParameterControls({ family, bindings, onChange }: { family: ScenarioFamily; bindings: Record<string, unknown>; onChange: (next: Record<string, unknown>) => void }) {
  return (
    <div className="form-grid">
      {family.parameter_domains.map((domain) => {
        const parameter = String(domain.parameter);
        const kind = String(domain.kind);
        if (kind === "enum") {
          const values = domain.values as unknown[];
          return <label key={parameter}><span>{parameter.replaceAll("_", " ")}</span><select value={String(bindings[parameter] ?? domain.default ?? values[0])} onChange={(event) => onChange({ ...bindings, [parameter]: event.target.value })}>{values.map((value) => <option value={String(value)} key={String(value)}>{String(value)}</option>)}</select></label>;
        }
        if (kind === "integer_range") {
          return <label key={parameter}><span>{parameter.replaceAll("_", " ")}</span><input type="number" min={Number(domain.minimum)} max={Number(domain.maximum)} step={Number(domain.step ?? 1)} value={Number(bindings[parameter] ?? domain.default ?? domain.minimum)} onChange={(event) => onChange({ ...bindings, [parameter]: Number(event.target.value) })} /></label>;
        }
        return <label className="checkbox-label" key={parameter}><input type="checkbox" checked={Boolean(bindings[parameter] ?? domain.default)} onChange={(event) => onChange({ ...bindings, [parameter]: event.target.checked })} /><span>{parameter.replaceAll("_", " ")}</span></label>;
      })}
    </div>
  );
}

function ScenarioLab({ families, activeFamilyId, onFamily, generated, onGenerated, onSelectNode, selectedNodeId, visualMode, onVisualMode }: {
  families: ScenarioFamily[];
  activeFamilyId?: string;
  onFamily: (id: string) => void;
  generated?: GeneratedScenario;
  onGenerated: (value: GeneratedScenario) => void;
  onSelectNode: (id: string) => void;
  selectedNodeId?: string;
  visualMode: VisualMode;
  onVisualMode: (mode: VisualMode) => void;
}) {
  const family = families.find((item) => item.family_id === activeFamilyId) ?? families[0];
  const [seed, setSeed] = useState(0);
  const [fault, setFault] = useState("");
  const [targetKind, setTargetKind] = useState("role");
  const [targetRef, setTargetRef] = useState("role.consume");
  const [observability, setObservability] = useState("complete");
  const [bindings, setBindings] = useState<Record<string, unknown>>({});
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    setFault("");
    setBindings({});
    setObservability(family?.observability_profiles[0] ?? "complete");
  }, [family?.family_id]);

  if (!family) return <p className="muted">No scenario families are available.</p>;
  const run = async () => {
    setRunning(true);
    setError(undefined);
    try {
      const faults = fault ? [{ application_id: "application.workbench.v1", operator_ref: fault, target_kind: targetKind, target_ref: targetRef || null, parameters: {} }] : [];
      const value = await generateScenario({
        scenario_id: `scenario.workbench.${family.family_class}.v1`,
        title: `Workbench: ${family.title}`,
        family_ref: family.family_id,
        parameter_bindings: bindings,
        faults,
        observability_profile: observability,
        seed,
      });
      onGenerated(value);
      onSelectNode(value.graph.nodes[0]?.node_id ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setRunning(false);
    }
  };
  return (
    <>
      <div className="case-heading">
        <div><span className="eyebrow">Scenario composer</span><h2>{family.title}</h2><p>{family.description}</p></div>
        <div className="heading-tags">{family.universe_axes.map((axis) => <Badge key={axis}>{axis.replaceAll("_", " ")}</Badge>)}</div>
      </div>
      <section className="composer">
        <div className="composer-controls">
          <label><span>Seed</span><input type="number" min="0" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label>
          <label><span>Fault operator</span><select value={fault} onChange={(event) => setFault(event.target.value)}><option value="">No semantic fault</option>{family.fault_operators.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Target kind</span><select value={targetKind} onChange={(event) => setTargetKind(event.target.value)}>{["role", "edge", "context", "effect", "observation", "resource", "system"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Target reference</span><input value={targetRef} onChange={(event) => setTargetRef(event.target.value)} placeholder="role.consume" /></label>
          <label><span>Observability profile</span><select value={observability} onChange={(event) => setObservability(event.target.value)}>{family.observability_profiles.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <ParameterControls family={family} bindings={bindings} onChange={setBindings} />
          <button type="button" className="primary-button" disabled={running} onClick={run}>{running ? "Generating…" : "Generate execution"}</button>
          {error ? <div className="error" role="alert">{error}</div> : null}
        </div>
        <div className="contract-panel">
          <span className="eyebrow">Contracts</span>
          <h3>Expected semantic checks</h3>
          {family.invariants.map((item) => <code className="contract-code" key={item}>{item}</code>)}
          <h3>Topology</h3><code className="contract-code">{family.topology_ref}</code>
          <h3>Coverage dimensions</h3>{family.universe_axes.map((axis) => <div className="relation-row" key={axis}><span>{axis.replaceAll("_", " ")}</span><small>declared</small></div>)}
        </div>
      </section>
      {generated ? (
        <>
          <div className="metrics">
            <Metric label="Ground-truth nodes" value={generated.ground_truth_summary.nodes ?? 0} />
            <Metric label="Observed nodes" value={generated.graph.nodes.length} />
            <Metric label="Derived relations" value={generated.graph.report.derived_relation_count} />
            <Metric label="Coverage points" value={generated.instance.coverage_points.length} />
            <Metric label="Oracle checks" value={generated.oracle.length} />
          </div>
          <section className="visual-section">
            <div className="section-heading"><div><span className="eyebrow">Generated instance</span><h2>{generated.instance.instance_id}</h2></div><VisualSwitcher value={visualMode} onChange={onVisualMode} /></div>
            {visualMode === "graph" ? <GraphCanvas graph={generated.graph} system={generated.observed_case.system} selectedNodeId={selectedNodeId} onSelect={onSelectNode} /> : null}
            {visualMode === "timeline" ? <TimelineView timeline={generated.timeline} selectedNodeId={selectedNodeId} onSelect={onSelectNode} /> : null}
            {visualMode === "semantics" ? <SemanticsView graph={generated.graph} /> : null}
          </section>
          <section className="visual-section"><div className="section-heading"><div><span className="eyebrow">Oracle</span><h2>Expected outcomes</h2></div></div><div className="oracle-grid">{generated.oracle.map((item) => <div className="oracle-card" key={item.invariant_ref}><Badge tone={item.expected_status === "satisfied" ? "good" : item.expected_status === "inconclusive" ? "warning" : "danger"}>{item.expected_status}</Badge><strong>{item.invariant_ref}</strong><p>{item.basis}</p></div>)}</div></section>
        </>
      ) : <div className="empty-state"><strong>Generate a scenario instance</strong><p>The Workbench will materialize ground truth, apply semantic and observability faults separately, assemble the execution graph, and render its timeline.</p></div>}
    </>
  );
}

function CompareWorkspace({
  cases,
  baselineCaseId,
  candidateCaseId,
  onBaseline,
  onCandidate,
  comparison,
  running,
  onRun,
  selectedDivergenceId,
  onSelectDivergence,
}: {
  cases: CaseSummary[];
  baselineCaseId?: string;
  candidateCaseId?: string;
  onBaseline: (id: string) => void;
  onCandidate: (id: string) => void;
  comparison?: SemanticComparison;
  running: boolean;
  onRun: () => void;
  selectedDivergenceId?: string;
  onSelectDivergence: (id: string) => void;
}) {
  const first = comparison?.divergences.find((item) => item.divergence_id === comparison.first_meaningful_divergence_ref);
  return (
    <>
      <div className="case-heading">
        <div><span className="eyebrow">Semantic execution comparison</span><h2>Find the first meaningful divergence</h2><p>Align operations by semantic role and structure rather than regenerated trace IDs or absolute position.</p></div>
      </div>
      <section className="compare-controls">
        <label><span>Baseline case</span><select value={baselineCaseId ?? ""} onChange={(event) => onBaseline(event.target.value)}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.title}</option>)}</select></label>
        <label><span>Candidate case</span><select value={candidateCaseId ?? ""} onChange={(event) => onCandidate(event.target.value)}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.title}</option>)}</select></label>
        <button type="button" className="primary-button" disabled={running || !baselineCaseId || !candidateCaseId || baselineCaseId === candidateCaseId} onClick={onRun}>{running ? "Comparing…" : "Compare executions"}</button>
      </section>
      {comparison ? (
        <>
          <div className="metrics">
            <Metric label="Aligned" value={comparison.summary.aligned_nodes} />
            <Metric label="Baseline only" value={comparison.summary.baseline_only_nodes} />
            <Metric label="Candidate only" value={comparison.summary.candidate_only_nodes} />
            <Metric label="Divergences" value={comparison.summary.divergence_count} detail={`${comparison.summary.consequential_divergence_count} consequential`} />
            <Metric label="Ambiguous" value={comparison.summary.ambiguous_alignments} />
          </div>
          {first ? <section className="first-divergence"><span className="eyebrow">First meaningful divergence · {Math.round(first.temporal_rank_ms ?? 0)} ms</span><h2>{first.title}</h2><p>{first.summary}</p><div className="heading-tags"><Badge tone={severityTone(first.severity)}>{first.severity}</Badge><Badge>{first.dimension}</Badge><Badge>{first.consequence}</Badge></div></section> : <section className="first-divergence success"><span className="eyebrow">No meaningful semantic divergence</span><h2>Executions remain semantically equivalent</h2></section>}
          <section className="comparison-grid">
            <div className="analysis-panel">
              <div className="section-heading"><div><span className="eyebrow">Alignment</span><h2>Synchronized operations</h2></div><Badge>{comparison.alignments.length}</Badge></div>
              <div className="alignment-list">
                {comparison.alignments.map((alignment) => (
                  <div className={`alignment-row alignment-${alignment.status}`} key={alignment.alignment_id}>
                    <div><small>Baseline</small><strong>{alignment.baseline_signature?.normalized_operation ?? alignment.baseline_node_ref ?? "—"}</strong><code>{alignment.baseline_signature?.node_kind ?? alignment.status}</code></div>
                    <div className="alignment-score"><span>↔</span><strong>{Math.round(alignment.score * 100)}%</strong></div>
                    <div><small>Candidate</small><strong>{alignment.candidate_signature?.normalized_operation ?? alignment.candidate_node_ref ?? "—"}</strong><code>{alignment.candidate_signature?.node_kind ?? alignment.status}</code></div>
                  </div>
                ))}
              </div>
            </div>
            <div className="analysis-panel">
              <div className="section-heading"><div><span className="eyebrow">Divergence navigator</span><h2>Consequential differences</h2></div><Badge tone={comparison.divergences.length ? "warning" : "good"}>{comparison.divergences.length}</Badge></div>
              <div className="analysis-list">
                {comparison.divergences.map((item) => (
                  <button type="button" className={`analysis-row ${item.divergence_id === selectedDivergenceId ? "selected" : ""}`} key={item.divergence_id} onClick={() => onSelectDivergence(item.divergence_id)}>
                    <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>
                    <div><strong>{item.title}</strong><p>{item.summary}</p></div>
                    <small>{item.temporal_rank_ms === undefined ? "unranked" : `${Math.round(item.temporal_rank_ms)} ms`}</small>
                  </button>
                ))}
              </div>
            </div>
          </section>
        </>
      ) : <div className="empty-state"><strong>Select two different cases</strong><p>The comparison engine will align their operations, suppress regenerated identity noise, classify structural/context/effect/timing differences, and rank the earliest consequential divergence.</p></div>}
    </>
  );
}

function DivergenceInspector({ divergence }: { divergence?: Divergence }) {
  if (!divergence) return null;
  return (
    <section className="finding-inspector">
      <span className="eyebrow">Selected divergence</span>
      <h3>{divergence.title}</h3>
      <div className="heading-tags"><Badge tone={severityTone(divergence.severity)}>{divergence.severity}</Badge><Badge>{divergence.dimension}</Badge></div>
      <p>{divergence.summary}</p>
      <dl>
        <dt>Consequence</dt><dd>{divergence.consequence}</dd>
        <dt>Confidence</dt><dd>{Math.round(divergence.confidence.score * 100)}%</dd>
        <dt>Baseline refs</dt><dd>{divergence.baseline_refs.length}</dd>
        <dt>Candidate refs</dt><dd>{divergence.candidate_refs.length}</dd>
      </dl>
      {divergence.limitations.map((item) => <div className="limitation" key={item}>{item}</div>)}
      <details><summary>Comparison JSON</summary><pre>{JSON.stringify(divergence, null, 2)}</pre></details>
    </section>
  );
}

export function App() {
  const [mode, setMode] = useState<WorkspaceMode>("explore");
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [families, setFamilies] = useState<ScenarioFamily[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string>();
  const [activeFamilyId, setActiveFamilyId] = useState<string>();
  const [detail, setDetail] = useState<CaseDetail>();
  const [graph, setGraph] = useState<AssembledGraph>();
  const [timeline, setTimeline] = useState<TimelineModel>();
  const [analysis, setAnalysis] = useState<AnalysisReport>();
  const [validation, setValidation] = useState<Record<string, unknown>>();
  const [generated, setGenerated] = useState<GeneratedScenario>();
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [selectedFindingId, setSelectedFindingId] = useState<string>();
  const [visualMode, setVisualMode] = useState<VisualMode>("graph");
  const [baselineCaseId, setBaselineCaseId] = useState<string>();
  const [candidateCaseId, setCandidateCaseId] = useState<string>();
  const [comparison, setComparison] = useState<SemanticComparison>();
  const [selectedDivergenceId, setSelectedDivergenceId] = useState<string>();
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    Promise.all([listCases(), listScenarioFamilies()])
      .then(([caseItems, familyItems]) => {
        setCases(caseItems);
        setFamilies(familyItems);
        setActiveCaseId(caseItems[0]?.case_id);
        setActiveFamilyId(familyItems[0]?.family_id);
        const baseline = caseItems.find((item) => item.title.toLowerCase().includes("baseline")) ?? caseItems[0];
        const candidate = caseItems.find((item) => item.title.toLowerCase().includes("failure")) ?? caseItems[1] ?? caseItems[0];
        setBaselineCaseId(baseline?.case_id);
        setCandidateCaseId(candidate?.case_id);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!activeCaseId) return;
    setError(undefined);
    Promise.all([
      getCase(activeCaseId),
      getAssembledGraph(activeCaseId),
      getTimeline(activeCaseId),
      getAnalysis(activeCaseId),
      getValidation(activeCaseId),
    ])
      .then(([caseDetail, graphPayload, timelinePayload, analysisPayload, validationPayload]) => {
        setDetail(caseDetail);
        setGraph(graphPayload);
        setTimeline(timelinePayload);
        setAnalysis(analysisPayload);
        setValidation(validationPayload);
        setSelectedNodeId(graphPayload.nodes[0]?.node_id);
        setSelectedFindingId(analysisPayload.findings[0]?.finding_id);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [activeCaseId]);

  const runComparison = async () => {
    if (!baselineCaseId || !candidateCaseId || baselineCaseId === candidateCaseId) return;
    setComparing(true);
    setError(undefined);
    try {
      const value = await compareCases(baselineCaseId, candidateCaseId);
      setComparison(value);
      setSelectedDivergenceId(value.first_meaningful_divergence_ref ?? value.divergences[0]?.divergence_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setComparing(false);
    }
  };

  const activeGraph = mode === "construct" ? generated?.graph : mode === "explore" ? graph : undefined;
  const selectedNode = useMemo(() => activeGraph?.nodes.find((node) => node.node_id === selectedNodeId), [activeGraph, selectedNodeId]);
  const selectedFinding = useMemo(() => analysis?.findings.find((item) => item.finding_id === selectedFindingId), [analysis, selectedFindingId]);
  const selectedDivergence = useMemo(() => comparison?.divergences.find((item) => item.divergence_id === selectedDivergenceId), [comparison, selectedDivergenceId]);
  const activeCase = cases.find((item) => item.case_id === activeCaseId);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div><span className="eyebrow">Milestone C</span><h1>Tracecase Workbench</h1></div>
        <div className="mode-switcher">
          <button type="button" className={mode === "explore" ? "active" : ""} onClick={() => setMode("explore")}>Explore cases</button>
          <button type="button" className={mode === "construct" ? "active" : ""} onClick={() => setMode("construct")}>Construct scenarios</button>
          <button type="button" className={mode === "compare" ? "active" : ""} onClick={() => setMode("compare")}>Compare executions</button>
        </div>
        <div className="top-actions">
          {mode === "compare" ? <Badge tone={comparison ? "good" : "neutral"}>{comparison ? "Comparison ready" : "Select cases"}</Badge> : <Badge tone={validation?.valid ? "good" : "warning"}>{validation?.valid ? "Bundle verified" : "Validation pending"}</Badge>}
        </div>
      </header>
      {error ? <div className="error global-error" role="alert">{error}</div> : null}
      <div className="workspace">
        <aside className="navigator">
          {mode === "explore" ? (
            <>
              <h2>Case bundles</h2>
              {cases.map((item) => (
                <button type="button" className={item.case_id === activeCaseId ? "case-button active" : "case-button"} key={item.case_id} onClick={() => setActiveCaseId(item.case_id)}>
                  <strong>{item.title}</strong><span>{item.category.replaceAll("_", " ")}</span><small>{item.node_count} nodes · {item.finding_count} findings · {item.violated_invariant_count} violations</small>
                </button>
              ))}
              {analysis?.findings.length ? <section className="nav-section"><h2>Findings</h2>{analysis.findings.map((finding) => <button type="button" className={finding.finding_id === selectedFindingId ? "case-button active" : "case-button"} key={finding.finding_id} onClick={() => { setSelectedFindingId(finding.finding_id); if (finding.node_refs[0]) setSelectedNodeId(finding.node_refs[0]); }}><strong>{finding.title}</strong><span>{finding.severity}</span><small>{finding.classification}</small></button>)}</section> : null}
              {graph ? <section className="nav-section"><h2>Execution nodes</h2><div className="node-list">{graph.nodes.map((node) => <button type="button" className={node.node_id === selectedNodeId ? "node-row selected" : "node-row"} key={node.node_id} onClick={() => setSelectedNodeId(node.node_id)}><span className="kind">{node.kind.replaceAll("_", " ")}</span><span className="operation">{node.operation}</span><span className={`status status-${node.status}`}>{node.status}</span></button>)}</div></section> : null}
            </>
          ) : mode === "construct" ? (
            <>
              <h2>Scenario families</h2>
              {families.map((family) => <button type="button" className={family.family_id === activeFamilyId ? "case-button active" : "case-button"} key={family.family_id} onClick={() => setActiveFamilyId(family.family_id)}><strong>{family.title}</strong><span>{family.family_class}</span><small>{family.universe_axes.length} universe axes · {family.fault_operators.length} faults</small></button>)}
              {generated ? <section className="nav-section"><h2>Generated nodes</h2><div className="node-list">{generated.graph.nodes.map((node) => <button type="button" className={node.node_id === selectedNodeId ? "node-row selected" : "node-row"} key={node.node_id} onClick={() => setSelectedNodeId(node.node_id)}><span className="kind">{node.kind.replaceAll("_", " ")}</span><span className="operation">{node.operation}</span><span className={`status status-${node.status}`}>{node.status}</span></button>)}</div></section> : null}
            </>
          ) : (
            <>
              <h2>Comparison cases</h2>
              {cases.map((item) => <div className="comparison-case" key={item.case_id}><strong>{item.title}</strong><span>{item.case_id === baselineCaseId ? "Baseline" : item.case_id === candidateCaseId ? "Candidate" : "Available"}</span></div>)}
              {comparison ? <section className="nav-section"><h2>Divergences</h2>{comparison.divergences.map((item) => <button type="button" className={item.divergence_id === selectedDivergenceId ? "case-button active" : "case-button"} key={item.divergence_id} onClick={() => setSelectedDivergenceId(item.divergence_id)}><strong>{item.title}</strong><span>{item.dimension}</span><small>{item.temporal_rank_ms === undefined ? "unranked" : `${Math.round(item.temporal_rank_ms)} ms`}</small></button>)}</section> : null}
            </>
          )}
        </aside>
        <section className="canvas">
          {mode === "explore" ? (
            <CaseWorkspace detail={detail} graph={graph} timeline={timeline} selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} visualMode={visualMode} onVisualMode={setVisualMode} analysis={analysis} selectedFindingId={selectedFindingId} onSelectFinding={setSelectedFindingId} />
          ) : mode === "construct" ? (
            <ScenarioLab families={families} activeFamilyId={activeFamilyId} onFamily={setActiveFamilyId} generated={generated} onGenerated={setGenerated} selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} visualMode={visualMode} onVisualMode={setVisualMode} />
          ) : (
            <CompareWorkspace cases={cases} baselineCaseId={baselineCaseId} candidateCaseId={candidateCaseId} onBaseline={setBaselineCaseId} onCandidate={setCandidateCaseId} comparison={comparison} running={comparing} onRun={runComparison} selectedDivergenceId={selectedDivergenceId} onSelectDivergence={setSelectedDivergenceId} />
          )}
        </section>
        <aside className="inspector">
          <span className="eyebrow">Inspector</span>
          {mode === "explore" && activeCase ? <div className="inspector-case"><strong>{activeCase.title}</strong><small>{activeCase.scenario_family ?? activeCase.case_id}</small></div> : null}
          {mode !== "compare" ? <NodeInspector node={selectedNode} graph={activeGraph} /> : null}
          {mode === "explore" ? <FindingInspector finding={selectedFinding} /> : null}
          {mode === "compare" ? <DivergenceInspector divergence={selectedDivergence} /> : null}
        </aside>
      </div>
    </main>
  );
}
