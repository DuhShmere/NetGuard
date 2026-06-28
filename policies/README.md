# NetGuard Policy Rules

Policies are defined as YAML files in this directory.

## Rule fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique rule ID (e.g. CISCO-001) |
| `name` | yes | Short human-readable name |
| `severity` | yes | `high`, `medium`, or `low` |
| `description` | yes | What the rule checks |
| `remediation_template` | no | Jinja2 template name to auto-fix (null = manual) |

## Adding a new rule

1. Add the rule entry to the relevant YAML file
2. Write a corresponding `check_*` function in `cisco/policy_checks.py` or `juniper/policy_checks.py`
3. Register the function in `run_all_checks()`
4. (Optional) Create a Jinja2 remediation template in `cisco/templates/` or `juniper/templates/`
