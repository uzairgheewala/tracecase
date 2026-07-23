from rest_framework.decorators import api_view
from rest_framework.response import Response
from tracecase_pathforge import PathforgeTraceBridge,pathforge_bindings

@api_view(["GET"])
def bindings(_request):
    return Response({"items":[item.model_dump(mode="json") for item in pathforge_bindings()]})

@api_view(["POST"])
def run(request):
    payload=request.data or {}; bridge=PathforgeTraceBridge(payload.get("binding_ref","pathforge.requirement-audit.v1")); case=bridge.demo_case(seed=int(payload.get("seed",1)),fault=payload.get("fault")); result=bridge.analyze(case)
    return Response({"result":result.model_dump(mode="json"),"case":case.model_dump(mode="json")})

@api_view(["POST"])
def compare(request):
    payload=request.data or {}; bridge=PathforgeTraceBridge(payload.get("binding_ref","pathforge.requirement-audit.v1")); baseline,candidate,comparison=bridge.compare_demo(seed=int(payload.get("seed",1)),fault=payload.get("fault","tenant-loss"))
    return Response({"baseline":baseline.specification.model_dump(mode="json"),"candidate":candidate.specification.model_dump(mode="json"),"comparison":comparison.model_dump(mode="json")})
