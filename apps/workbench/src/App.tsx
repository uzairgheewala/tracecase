import { useEffect, useMemo, useState } from "react";
import { getCase, getGraph, getValidation, listCases } from "./api";
import type { CaseDetail, CaseSummary, GraphNode, GraphPayload } from "./types";

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function NodeList({ graph, selected, onSelect }: { graph: GraphPayload; selected?: string; onSelect: (id: string) => void }) {
  return (
    <div className="node-list" role="list" aria-label="Execution nodes">
      {graph.nodes.map((node) => (
        <button
          type="button"
          className={node.node_id === selected ? "node-row selected" : "node-row"}
          key={node.node_id}
          onClick={() => onSelect(node.node_id)}
        >
          <span className="kind">{node.kind.replaceAll("_", " ")}</span>
          <span className="operation">{node.operation}</span>
          <span className={`status status-${node.status}`}>{node.status}</span>
        </button>
      ))}
    </div>
  );
}

function RelationStrip({ graph }: { graph: GraphPayload }) {
  return (
    <div className="relation-strip" aria-label="Execution flow">
      {graph.nodes.map((node, index) => (
        <div className="flow-item" key={node.node_id}>
          <div className="flow-node">
            <small>{node.kind.replaceAll("_", " ")}</small>
            <strong>{node.operation}</strong>
          </div>
          {index < graph.nodes.length - 1 ? <span className="arrow" aria-hidden="true">→</span> : null}
        </div>
      ))}
    </div>
  );
}

function Inspector({ node, graph }: { node?: GraphNode; graph?: GraphPayload }) {
  if (!node || !graph) {
    return <p className="muted">Select a node to inspect its semantic fields and references.</p>;
  }
  const incoming = graph.relations.filter((relation) => relation.target_ref === node.node_id);
  const outgoing = graph.relations.filter((relation) => relation.source_ref === node.node_id);
  return (
    <div className="inspector-content">
      <div>
        <span className="eyebrow">{node.kind.replaceAll("_", " ")}</span>
        <h2>{node.operation}</h2>
        <code>{node.node_id}</code>
      </div>
      <dl>
        <dt>Component</dt><dd>{node.component_ref}</dd>
        <dt>Status</dt><dd>{node.status}</dd>
        <dt>Start</dt><dd>{node.timing.normalized_timestamp ?? node.timing.raw_timestamp}</dd>
        <dt>Contexts</dt><dd>{node.context_refs.length || "None"}</dd>
        <dt>Effects</dt><dd>{node.effect_refs.length || "None"}</dd>
        <dt>Evidence</dt><dd>{node.observation_refs.length}</dd>
      </dl>
      <section>
        <h3>Relationships</h3>
        {[...incoming, ...outgoing].map((relation) => (
          <div className="relation-row" key={relation.relation_id}>
            <span>{relation.kind.replaceAll("_", " ")}</span>
            <small>{relation.derivation}</small>
          </div>
        ))}
      </section>
      <details>
        <summary>Canonical JSON</summary>
        <pre>{JSON.stringify(node, null, 2)}</pre>
      </details>
    </div>
  );
}

export function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string>();
  const [detail, setDetail] = useState<CaseDetail>();
  const [graph, setGraph] = useState<GraphPayload>();
  const [validation, setValidation] = useState<Record<string, unknown>>();
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    listCases()
      .then((items) => {
        setCases(items);
        setActiveCaseId(items[0]?.case_id);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!activeCaseId) return;
    setError(undefined);
    Promise.all([getCase(activeCaseId), getGraph(activeCaseId), getValidation(activeCaseId)])
      .then(([caseDetail, graphPayload, validationPayload]) => {
        setDetail(caseDetail);
        setGraph(graphPayload);
        setValidation(validationPayload);
        setSelectedNodeId(graphPayload.nodes[0]?.node_id);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [activeCaseId]);

  const selectedNode = useMemo(
    () => graph?.nodes.find((node) => node.node_id === selectedNodeId),
    [graph, selectedNodeId],
  );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Milestone A</span>
          <h1>Tracecase Workbench</h1>
        </div>
        <div className="top-actions">
          <span className={validation?.valid ? "badge good" : "badge"}>
            {validation?.valid ? "Bundle verified" : "Not verified"}
          </span>
        </div>
      </header>

      {error ? <div className="error" role="alert">{error}</div> : null}

      <div className="workspace">
        <aside className="navigator">
          <h2>Cases</h2>
          {cases.length === 0 ? <p className="muted">Start the API and generate the sample bundle.</p> : null}
          {cases.map((item) => (
            <button
              type="button"
              className={item.case_id === activeCaseId ? "case-button active" : "case-button"}
              key={item.case_id}
              onClick={() => setActiveCaseId(item.case_id)}
            >
              <strong>{item.title}</strong>
              <span>{item.category.replaceAll("_", " ")}</span>
              <small>{item.node_count} nodes · {item.effect_count} effects</small>
            </button>
          ))}
          {graph ? (
            <section className="nav-section">
              <h2>Execution</h2>
              <NodeList graph={graph} selected={selectedNodeId} onSelect={setSelectedNodeId} />
            </section>
          ) : null}
        </aside>

        <section className="canvas">
          {detail && graph ? (
            <>
              <div className="case-heading">
                <div>
                  <span className="eyebrow">{detail.specification.category.replaceAll("_", " ")}</span>
                  <h2>{detail.specification.title}</h2>
                  <p>{detail.specification.description}</p>
                </div>
                <code>{detail.specification.case_id}</code>
              </div>
              <div className="metrics">
                <Metric label="Components" value={detail.system.components.length} />
                <Metric label="Nodes" value={detail.summary.nodes} />
                <Metric label="Relations" value={detail.summary.relations} />
                <Metric label="Observations" value={detail.summary.observations} />
                <Metric label="Effects" value={detail.summary.effects} />
              </div>
              <section className="visual-section">
                <div className="section-heading">
                  <div><span className="eyebrow">Execution graph</span><h2>Semantic flow</h2></div>
                  <span className="badge">{graph.relations.length} typed edges</span>
                </div>
                <RelationStrip graph={graph} />
              </section>
              <section className="visual-section">
                <div className="section-heading"><div><span className="eyebrow">System model</span><h2>Components</h2></div></div>
                <div className="component-grid">
                  {detail.system.components.map((component) => (
                    <div className="component" key={component.component_id}>
                      <span>{component.kind.replaceAll("_", " ")}</span>
                      <strong>{component.name}</strong>
                      <code>{component.component_id}</code>
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : <p className="muted">Loading case evidence…</p>}
        </section>

        <aside className="inspector">
          <span className="eyebrow">Inspector</span>
          <Inspector node={selectedNode} graph={graph} />
        </aside>
      </div>
    </main>
  );
}
