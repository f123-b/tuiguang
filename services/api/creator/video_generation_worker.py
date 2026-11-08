"""Independent local GPU queue, sharing the narration model's inference lock."""

import argparse
import time

from .db import SessionLocal
from .video_generation import process_generation_jobs


def tick():
    with SessionLocal() as db:
        process_generation_jobs(db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        tick()
        if args.once:
            break
        time.sleep(10)
