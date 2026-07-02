import pytest
from cisco.policy_checks import run_all_checks

COMPLIANT_CONFIG = """
ip ssh version 2
ntp server 10.0.0.1
no ip http server
snmp-server community NetGuard-SNMP RO
line vty 0 15
 transport input ssh
ip access-list extended NETGUARD-ACL
 permit tcp any any eq 22
 permit icmp any any
 deny ip any any
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

def test_missing_ssh_version_flagged():
    violations = run_all_checks(NON_COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "CISCO-001" in ids

def test_missing_ntp_flagged():
    violations = run_all_checks(NON_COMPLIANT_CONFIG)
    ids = [v["rule_id"] for v in violations]
    assert "CISCO-003" in ids

def test_fully_compliant_no_violations():
    violations = run_all_checks(COMPLIANT_CONFIG)
    assert violations == []
