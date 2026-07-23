from tracecase_model import Component, ComponentKind


def test_namespaced_extensions_round_trip() -> None:
    component = Component(
        component_id="component.worker",
        name="worker",
        kind=ComponentKind.WORKER,
        extensions={"python.celery": {"queue": "imports"}},
    )
    restored = Component.model_validate(component.model_dump(mode="json"))
    assert restored.extensions["python.celery"]["queue"] == "imports"
