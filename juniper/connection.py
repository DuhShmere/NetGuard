from jnpr.junos import Device as JunosDevice

def get_connection(host: str, username: str, password: str, port: int = 830):
    """Return an open PyEZ Device connection to a Juniper device."""
    dev = JunosDevice(host=host, user=username, passwd=password, port=port)
    dev.open()
    return dev
