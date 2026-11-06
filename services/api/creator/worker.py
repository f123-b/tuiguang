import argparse
import time

from .db import SessionLocal
from .jobs import process_pending, schedule_due


def tick():
    from .video import process_render_jobs

    with SessionLocal() as db:
        schedule_due(db)
        process_pending(db)
        process_render_jobs(db)
        from .learning import weekly_reviews
        weekly_reviews(db)
        from .notifications import sync
        sync(db)
        db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        tick()
        if args.once:
            break
        time.sleep(15)
