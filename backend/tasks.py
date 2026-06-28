from celery import Celery
import os

celery_app = Celery(
    "netguard",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

@celery_app.task
def poll_all_devices():
    """Triggered by APScheduler — collects config from all devices."""
    # TODO: query device inventory, dispatch per-vendor collector
    pass

@celery_app.task
def run_remediation(device_id: int, violation: dict):
    """Auto-remediate a single policy violation."""
    # TODO: route to cisco.remediate or juniper.remediate by vendor
    pass
