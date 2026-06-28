from netmiko import ConnectHandler
from typing import Optional

def get_connection(host: str, username: str, password: str,
                   platform: str = "cisco_ios", port: int = 22):
    """Return an active Netmiko SSH connection to a Cisco device."""
    return ConnectHandler(
        device_type=platform,
        host=host,
        username=username,
        password=password,
        port=port,
    )
