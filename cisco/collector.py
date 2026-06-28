from cisco.connection import get_connection
from cisco.parser import parse_output

def collect_config(host: str, username: str, password: str,
                   platform: str = "cisco_ios") -> dict:
    """SSH into a Cisco device and pull running config + key show commands."""
    with get_connection(host, username, password, platform) as conn:
        running_config = conn.send_command("show running-config")
        version        = conn.send_command("show version")
        interfaces     = conn.send_command("show interfaces")
        ip_route       = conn.send_command("show ip route summary")

    return {
        "running_config": running_config,
        "version":        parse_output("show_version", version),
        "interfaces":     parse_output("show_interfaces", interfaces),
        "ip_route":       ip_route,
    }
