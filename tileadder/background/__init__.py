"""
Background task processing for tileadder. Processes things like map cat
additions and other long-running tasks.
"""

import time

from structlog import get_logger

from .core import SafeScheduler

from .mapcat import ProcessMapCat

log = get_logger()


def background(run_once: bool = False):
    scheduler = SafeScheduler()
    # Set scheduling...

    all_tasks = (
        ProcessMapCat(name="process_mapcat"),
    )

    for task in all_tasks:
        log.debug(
            "background.schedule_task",
            task_name=task.name,
            task_every_seconds=task.every.total_seconds(),
        )
        scheduler.every(task.every.total_seconds()).seconds.do(task.task)

    log.debug("background.run_all.start")
    # ...and run it all on startup.
    scheduler.run_all()
    log.debug("background.run_all.end")

    # ...begin scheduling operations.
    while not run_once:
        try:
            scheduler.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            break