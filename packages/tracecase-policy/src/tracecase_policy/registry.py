from __future__ import annotations

from tracecase_model import SensitivityLabel

from .models import ExportProfile, PolicyRule, RedactionAction, RedactionPolicy


def default_internal_policy() -> RedactionPolicy:
    return RedactionPolicy(
        policy_id="policy.internal.v1",
        title="Internal diagnostic export",
        profile=ExportProfile.INTERNAL,
        rules=(
            PolicyRule(rule_id="credential.reject", labels=(SensitivityLabel.CREDENTIAL,), action=RedactionAction.REJECT, priority=5),
        ),
        prohibited_patterns=(r"(?i)authorization:\s*bearer\s+\S+", r"(?i)password\s*[=:]\s*\S+"),
    )


def default_shareable_policy() -> RedactionPolicy:
    return RedactionPolicy(
        policy_id="policy.shareable.v1",
        title="Shareable engineering case",
        profile=ExportProfile.SHAREABLE,
        rules=(
            PolicyRule(rule_id="credential.remove", labels=(SensitivityLabel.CREDENTIAL,), action=RedactionAction.REMOVE, priority=1, description="Credentials never leave the collection environment."),
            PolicyRule(rule_id="secret-key.remove", key_pattern=r"(?i)(authorization|cookie|password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)", action=RedactionAction.REMOVE, priority=2),
            PolicyRule(rule_id="student.tokenize", labels=(SensitivityLabel.STUDENT_RECORD,), action=RedactionAction.TOKENIZE, priority=10),
            PolicyRule(rule_id="user.tokenize", labels=(SensitivityLabel.USER_IDENTIFIER,), action=RedactionAction.TOKENIZE, priority=11),
            PolicyRule(rule_id="tenant.tokenize", labels=(SensitivityLabel.TENANT_IDENTIFIER,), action=RedactionAction.TOKENIZE, priority=12),
            PolicyRule(rule_id="free-text.summarize", labels=(SensitivityLabel.FREE_TEXT,), action=RedactionAction.SUMMARIZE, priority=20),
            PolicyRule(rule_id="query.digest", labels=(SensitivityLabel.QUERY_TEXT,), action=RedactionAction.DIGEST, priority=21),
            PolicyRule(rule_id="payload.digest", labels=(SensitivityLabel.PAYLOAD_DERIVED,), action=RedactionAction.DIGEST, priority=22),
            PolicyRule(rule_id="principal.tokenize", path_glob="*.identities.principal_id", action=RedactionAction.TOKENIZE, priority=8),
            PolicyRule(rule_id="tenant-identity.tokenize", path_glob="*.identities.tenant_id", action=RedactionAction.TOKENIZE, priority=8),
            PolicyRule(rule_id="session.tokenize", path_glob="*.identities.session_id", action=RedactionAction.TOKENIZE, priority=8),
            PolicyRule(rule_id="source-native.tokenize", path_glob="*.provenance.source_native_id", action=RedactionAction.TOKENIZE, priority=30),
        ),
        prohibited_patterns=(
            r"(?i)bearer\s+[a-z0-9._~+/-]+=*",
            r"AKIA[0-9A-Z]{16}",
            r"(?i)(password|passwd|secret|api[_-]?key)\s*[=:]\s*[^\s,}\]]+",
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        ),
        attributes={"unknown_sensitive_action": "reject", "copy_unknown_supplements": False},
    )


def default_public_policy() -> RedactionPolicy:
    base = default_shareable_policy()
    return base.model_copy(
        update={
            "policy_id": "policy.public.v1",
            "title": "Public issue attachment",
            "profile": ExportProfile.PUBLIC,
            "rules": base.rules + (
                PolicyRule(rule_id="network.mask", labels=(SensitivityLabel.NETWORK_METADATA,), action=RedactionAction.MASK, priority=15),
                PolicyRule(rule_id="internal.digest", labels=(SensitivityLabel.INTERNAL,), action=RedactionAction.DIGEST, priority=50),
            ),
        }
    )


def policy_registry() -> tuple[RedactionPolicy, ...]:
    return (default_internal_policy(), default_shareable_policy(), default_public_policy())


def get_policy(policy_id: str) -> RedactionPolicy:
    for policy in policy_registry():
        if policy.policy_id == policy_id:
            return policy
    raise KeyError(policy_id)
