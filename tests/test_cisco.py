import pytest
from cisco.policy_checks import run_all_checks

COMPLIANT_CONFIG = """
ip ssh version 2
ntp server 10.0.0.1
no ip http server
"""

NON_COMPLIANT_CONFIG = """
transport input telnet
snmp-server community public RO
"""

def test_compliant_config_passes():
    violations = run_all_checks(COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "CISCO-001" not in ids
    assert "CISCO-003" not in ids

def test_telnet_detected():
    violations = run_all_checks(NON_COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "CISCO-002" in ids

def test_default_snmp_detected():
    violations = run_all_checks(NON_COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "CISCO-004" in ids
