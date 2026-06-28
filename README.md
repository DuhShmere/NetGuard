# NetGuard

**Network Compliance and Drift Detection Platform**

Continuously audits Cisco and Juniper device configurations against a defined
policy baseline, detects drift in real time, auto-remediates safe violations,
and rolls back unsafe changes before they cause outages.

## Stack

| Layer | Tech |
|---|---|
| Backend API | Python, FastAPI, SQLAlchemy, PostgreSQL |
| Task queue | Celery + Redis |
| Cisco devices | Netmiko, TextFSM / NTC templates |
| Juniper devices | PyEZ (junos-eznc), NETCONF |
| Frontend | Vanilla JS + WebSocket live feed |
| Windows scripts | PowerShell |

## Quick start

```bash
cp .env.example .env           # fill in your credentials
docker-compose up -d           # start PostgreSQL + Redis
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open `dashboard/index.html` in your browser.

## Project layout

```
netguard/
├── backend/        # FastAPI app, models, routes, scheduler, Celery tasks
├── cisco/          # Netmiko collector, TextFSM parser, policy checks, remediation
├── juniper/        # PyEZ collector, NETCONF, policy checks, commit/rollback
├── policies/       # YAML compliance rule definitions (one file per vendor)
├── dashboard/      # HTML/JS compliance dashboard + WebSocket client
├── scripts/        # PowerShell inventory + report export
└── tests/          # pytest test suite
```

## Team roles

| Role | Owns |
|---|---|
| Backend engineer | `backend/` — FastAPI, DB models, routes, APScheduler, Celery |
| Cisco engineer | `cisco/` — Netmiko, TextFSM parsing, IOS policy checks |
| Juniper engineer | `juniper/` — PyEZ, NETCONF, Junos policy checks |
| Frontend + PowerShell engineer | `dashboard/`, `scripts/` |

## Adding a compliance rule

1. Add the rule to `policies/cisco_baseline.yaml` or `policies/juniper_baseline.yaml`
2. Write a `check_*` function in `cisco/policy_checks.py` or `juniper/policy_checks.py`
3. Register it inside `run_all_checks()`
4. Optionally add a Jinja2 remediation template in `cisco/templates/` or `juniper/templates/`

## Running tests

```bash
pytest tests/
```
