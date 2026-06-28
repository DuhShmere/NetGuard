import pytest
from juniper.policy_checks import run_all_checks

COMPLIANT_CONFIG = """
system {
    root-authentication { encrypted-password "..."; }
    syslog { host 10.0.0.5 { any any; } }
}
firewall { filter PROTECT-RE { term accept-ssh { ... } } }
"""

NON_COMPLIANT_CONFIG = """
system {
    services { ssh; }
}
"""

def test_missing_syslog_flagged():
    violations = run_all_checks(NON_COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "JNR-003" in ids

def test_missing_firewall_flagged():
    violations = run_all_checks(NON_COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "JNR-004" in ids

def test_compliant_passes_root_check():
    violations = run_all_checks(COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "JNR-001" not in ids
