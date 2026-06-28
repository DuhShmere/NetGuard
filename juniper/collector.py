from juniper.connection import get_connection
from jnpr.junos.utils.config import Config

def collect_config(host: str, username: str, password: str) -> dict:
    """Pull running config and key operational data from a Juniper device."""
    dev = get_connection(host, username, password)
    try:
        config_xml  = dev.rpc.get_config(options={"format": "text"}).text
        interfaces  = dev.rpc.get_interface_information(terse=True)
        bgp_summary = dev.rpc.get_bgp_summary_information()
        return {
            "running_config": config_xml,
            "interfaces":     interfaces,
            "bgp_summary":    bgp_summary,
        }
    finally:
        dev.close()
