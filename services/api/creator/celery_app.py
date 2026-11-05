import os

from celery import Celery

from .worker import tick

app = Celery("creator", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={"persistent-db-tick": {"task": "creator.tick", "schedule": 30.0}},
)


@app.task(name="creator.tick", ignore_result=True)
def scheduled_tick():
    tick()
