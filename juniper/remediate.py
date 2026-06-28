from juniper.connection import get_connection
from jnpr.junos.utils.config import Config
from jinja2 import Environment, FileSystemLoader
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def push_remediation(host: str, username: str, password: str,
                     template_name: str, context: dict = {}) -> dict:
    """Render a Jinja2 set-format template and commit it to a Juniper device."""
    template  = jinja_env.get_template(f"{template_name}.j2")
    config_str = template.render(**context)

    dev = get_connection(host, username, password)
    try:
        cu = Config(dev)
        cu.lock()
        cu.load(config_str, format="set")
        diff = cu.diff()
        cu.commit()
        cu.unlock()
        return {"status": "committed", "diff": diff}
    except Exception as e:
        cu.rollback()
        cu.unlock()
        return {"status": "rolled_back", "error": str(e)}
    finally:
        dev.close()
