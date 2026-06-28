from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()

def start_scheduler():
    from backend.tasks import poll_all_devices
    scheduler.add_job(
        poll_all_devices,
        trigger=IntervalTrigger(minutes=10),
        id="poll_devices",
        replace_existing=True,
    )
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
