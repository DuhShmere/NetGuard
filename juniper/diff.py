from juniper.connection import get_connection
from jnpr.junos.utils.config import Config

def get_config_diff(host: str, username: str, password: str) -> str:
    """Return the diff between candidate and running config (without committing)."""
    dev = get_connection(host, username, password)
    try:
        cu = Config(dev)
        return cu.diff() or "No differences"
    finally:
        dev.close()
