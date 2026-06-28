from cisco.connection import get_connection
from jinja2 import Environment, FileSystemLoader
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def push_remediation(host: str, username: str, password: str,
                     template_name: str, context: dict = {},
                     platform: str = "cisco_ios") -> dict:
    """Render a Jinja2 config template and push it to a Cisco device."""
    template = jinja_env.get_template(f"{template_name}.j2")
    config_commands = template.render(**context).strip().splitlines()

    with get_connection(host, username, password, platform) as conn:
        output = conn.send_config_set(config_commands)
        conn.save_config()

    return {"status": "pushed", "output": output}

def verify_reachability(host: str, username: str, password: str,
                        target_ip: str, platform: str = "cisco_ios") -> bool:
    """Ping target_ip from the device. Returns True if reachable."""
    with get_connection(host, username, password, platform) as conn:
        result = conn.send_command(f"ping {target_ip} repeat 3")
    return "!!!" in result or "Success rate is 100" in result
