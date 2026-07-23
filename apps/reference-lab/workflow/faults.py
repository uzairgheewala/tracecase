from dataclasses import dataclass
from django.conf import settings

@dataclass(frozen=True)
class FaultContext:
    operator_ref: str | None

    def enabled(self, operator_ref: str) -> bool:
        return bool(settings.TRACECASE_LAB_FAULTS_ENABLED and self.operator_ref == operator_ref)

SUPPORTED_FAULTS = {
    "fault.context.drop.v1",
    "fault.ordering.publish-before-commit.v1",
    "fault.effect.duplicate.v1",
    "fault.consistency.stale-cache.v1",
    "fault.contract.schema-skew.v1",
    "fault.observability.break-link.v1",
    "fault.privacy.capture-secret.v1",
    "fault.external.timeout-after-effect.v1",
}
