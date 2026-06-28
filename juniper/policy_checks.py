"""
Evaluate Juniper running config (text format) against compliance rules.
Returns a list of violation dicts: {rule_id, severity, description}
"""

def check_root_login(config: str) -> dict | None:
    if "root-authentication" not in config:
        return {"rule_id": "JNR-001", "severity": "high",
                "description": "Root authentication not configured — root login may be open"}

def check_ssh_key_auth(config: str) -> dict | None:
    if "ssh" not in config or "authentication-order" not in config:
        return {"rule_id": "JNR-002", "severity": "medium",
                "description": "SSH key-based authentication not enforced"}

def check_syslog(config: str) -> dict | None:
    if "syslog" not in config:
        return {"rule_id": "JNR-003", "severity": "medium",
                "description": "No syslog server configured"}

def check_firewall_filter(config: str) -> dict | None:
    if "firewall" not in config:
        return {"rule_id": "JNR-004", "severity": "high",
                "description": "No firewall filter defined"}

def run_all_checks(config: str) -> list:
    checks = [check_root_login, check_ssh_key_auth, check_syslog, check_firewall_filter]
    return [v for c in checks if (v := c(config)) is not None]
