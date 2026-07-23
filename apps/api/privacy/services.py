from __future__ import annotations

from pathlib import Path
from django.conf import settings
from tracecase_policy import PolicyEngine, ShareableBundleExporter, get_policy, policy_registry
from cases.services import CaseRepository


class PrivacyService:
    def __init__(self) -> None:
        self.repository = CaseRepository()

    def policies(self):
        return policy_registry()

    def inventory(self, case_id: str, policy_id: str):
        reader = self.repository.get_reader(case_id)
        policy = get_policy(policy_id)
        return PolicyEngine(policy).inventory(reader.load_case())

    def preview(self, case_id: str, policy_id: str):
        reader = self.repository.get_reader(case_id)
        policy = get_policy(policy_id)
        _, report = PolicyEngine(policy).apply(reader.load_case())
        return report

    def export(self, case_id: str, policy_id: str):
        reader = self.repository.get_reader(case_id)
        policy = get_policy(policy_id)
        export_root = Path(settings.TRACECASE_BUNDLE_ROOT) / "exports"
        export_root.mkdir(parents=True, exist_ok=True)
        safe_case = case_id.replace(".", "-")
        output = export_root / f"shareable-{safe_case}.tracecase"
        archive = export_root / f"shareable-{safe_case}.tracecase.zip"
        return ShareableBundleExporter(policy).export(reader, output, archive_path=archive, overwrite=True)
