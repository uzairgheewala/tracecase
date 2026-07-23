from __future__ import annotations
from collections import defaultdict, deque
from tracecase_graph import AssembledExecutionGraph
from tracecase_model import ExecutionCase
from .models import GraphNeighborhood, QueryIndexSummary

class CaseQueryIndex:
    def __init__(self, case: ExecutionCase, graph: AssembledExecutionGraph) -> None:
        self.case=case; self.graph=graph
        self.nodes={n.node_id:n for n in graph.nodes}; self.relations={r.relation_id:r for r in graph.relations}
        self.by_component=defaultdict(list); self.by_operation=defaultdict(list); self.by_identity=defaultdict(list); self.by_effect=defaultdict(list)
        for node in graph.nodes:
            self.by_component[node.component_ref].append(node.node_id); self.by_operation[node.operation].append(node.node_id)
            for name,value in node.identities.model_dump(exclude_none=True).items():
                if isinstance(value,(str,int)): self.by_identity[f"{name}:{value}"].append(node.node_id)
        for group in graph.effect_groups: self.by_effect[group.logical_effect_key].extend(group.member_effect_refs)
        self.adjacency=defaultdict(list)
        for relation in graph.relations:
            self.adjacency[relation.source_ref].append((relation.target_ref,relation.relation_id)); self.adjacency[relation.target_ref].append((relation.source_ref,relation.relation_id))

    def summary(self) -> QueryIndexSummary:
        return QueryIndexSummary(index_id=f"query-index.{self.case.specification.case_id}",node_count=len(self.nodes),component_count=len(self.by_component),operation_count=len(self.by_operation),identity_value_count=len(self.by_identity),effect_key_count=len(self.by_effect))

    def neighborhood(self, center_ref: str, depth: int=1) -> GraphNeighborhood:
        if center_ref not in self.nodes: raise KeyError(center_ref)
        seen={center_ref}; rels=set(); queue=deque([(center_ref,0)])
        while queue:
            node,d=queue.popleft()
            if d>=depth: continue
            for other,relation in self.adjacency[node]:
                rels.add(relation)
                if other not in seen: seen.add(other); queue.append((other,d+1))
        return GraphNeighborhood(center_ref=center_ref,depth=depth,node_refs=tuple(sorted(seen)),relation_refs=tuple(sorted(rels)))
