from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    ROOT / "packages" / "tracecase-model" / "src": {
        "django",
        "rest_framework",
        "celery",
        "opentelemetry",
        "tracecase_bundle",
        "tracecase_cli",
        "tracecase_scenarios",
        "tracecase_collectors",
        "tracecase_graph",
    },
    ROOT / "packages" / "tracecase-bundle" / "src": {
        "django",
        "rest_framework",
        "celery",
        "opentelemetry",
        "tracecase_cli",
        "tracecase_scenarios",
        "tracecase_collectors",
        "tracecase_graph",
    },
    ROOT / "packages" / "tracecase-scenarios" / "src": {
        "django",
        "rest_framework",
        "celery",
        "opentelemetry",
        "tracecase_bundle",
        "tracecase_collectors",
        "tracecase_graph",
        "tracecase_cli",
    },
    ROOT / "packages" / "tracecase-collectors" / "src": {
        "django",
        "rest_framework",
        "celery",
        "tracecase_bundle",
        "tracecase_scenarios",
        "tracecase_graph",
        "tracecase_cli",
    },
    ROOT / "packages" / "tracecase-graph" / "src": {
        "django",
        "rest_framework",
        "celery",
        "opentelemetry",
        "tracecase_bundle",
        "tracecase_scenarios",
        "tracecase_collectors",
        "tracecase_cli",
    },
}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def main() -> int:
    violations: list[str] = []
    for package_root, forbidden in RULES.items():
        for path in package_root.rglob("*.py"):
            invalid = imported_roots(path) & forbidden
            if invalid:
                violations.append(f"{path.relative_to(ROOT)} imports forbidden roots: {sorted(invalid)}")
    if violations:
        print("Architecture dependency violations:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Architecture dependency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
