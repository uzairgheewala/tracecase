from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from cases.services import CaseRepository
from tracecase_compat import BundleHealthScanner,CaseQueryIndex,CompatibilityEngine
repository=CaseRepository()

@api_view(["GET"])
def case_health(_request,case_id):
    try: reader=repository.get_reader(case_id)
    except FileNotFoundError: return Response({"detail":"Case not found"},status=status.HTTP_404_NOT_FOUND)
    return Response({"compatibility":CompatibilityEngine().assess(reader).model_dump(mode="json"),"health":BundleHealthScanner().scan(reader).model_dump(mode="json")})

@api_view(["GET"])
def case_neighborhood(request,case_id):
    try:
        reader=repository.get_reader(case_id); case=reader.load_case(); graph=repository.get_assembled_graph(case_id)
    except FileNotFoundError: return Response({"detail":"Case not found"},status=status.HTTP_404_NOT_FOUND)
    node_ref=request.query_params.get("node_ref") or graph.nodes[0].node_id
    depth=int(request.query_params.get("depth","1"))
    try: result=CaseQueryIndex(case,graph).neighborhood(node_ref,depth=depth)
    except KeyError: return Response({"detail":"Node not found"},status=status.HTTP_404_NOT_FOUND)
    return Response(result.model_dump(mode="json"))
