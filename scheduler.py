from apscheduler.schedulers.background import BackgroundScheduler
from typing import Callable
import datetime


class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def schedule_job(self, func:Callable, run_in_minutes:int):
        run_at = datetime.datetime.now() + datetime.timedelta(minutes=run_in_minutes)
        self.scheduler.add_job(func, 'date', run_date=run_at)
