import textfsm
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "ntc_templates")

def parse_output(template_name: str, raw_output: str) -> list:
    """Parse IOS command output using a TextFSM/NTC template."""
    template_path = os.path.join(TEMPLATE_DIR, f"{template_name}.textfsm")
    if not os.path.exists(template_path):
        return [{"raw": raw_output}]
    with open(template_path) as f:
        fsm = textfsm.TextFSM(f)
    return [dict(zip(fsm.header, row)) for row in fsm.ParseText(raw_output)]
