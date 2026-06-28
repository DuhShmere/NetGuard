"""
Evaluate a Cisco running config against compliance rules.
Returns a list of violation dicts: {rule_id, severity, description}
"""

def check_ssh_version(config: str) -> dict | None:
    if "ip ssh version 2" not in config:
        return {"rule_id": "CISCO-001", "severity": "high",
                "description": "SSH v2 not enforced"}

def check_telnet_disabled(config: str) -> dict | None:
    if "transport input telnet" in config or "transport input all" in config:
        return {"rule_id": "CISCO-002", "severity": "high",
                "description": "Telnet enabled on one or more VTY lines"}

def check_ntp(config: str) -> dict | None:
    if "ntp server" not in config:
        return {"rule_id": "CISCO-003", "severity": "medium",
                "description": "No NTP server configured"}

def check_snmp_community(config: str) -> dict | None:
    if "snmp-server community public" in config or "snmp-server community private" in config:
        return {"rule_id": "CISCO-004", "severity": "high",
                "description": "Default SNMP community string in use"}

def run_all_checks(config: str) -> list:
    checks = [check_ssh_version, check_telnet_disabled, check_ntp, check_snmp_community]
    return [v for c in checks if (v := c(config)) is not None]
