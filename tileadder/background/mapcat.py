"""
Processes mapcats in the background and updates their definitions.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from tileadder.settings import Settings
from tileadder.server.database import EngineManager

from datetime import timedelta, datetime, timezone

from tileadder.service.mapcat import MapCatRegistration

from structlog import get_logger


from .task import Task

class ProcessMapCat(Task):
    """
    A background task that processes the mapcats that are stored in the
    tilemaker database and updates them.
    """

    def on_call(self):
        manager = EngineManager(database_url=Settings().database_url)
        with manager.session as session:
            self.core(session=session)

    def core(self, session: Session):
        """
        The core of the task that does the actual work. This is called by
        on_call() and is passed a session that can be used to query the
        database.
        """

        logger = get_logger()

        query = select(MapCatRegistration)

        result = session.execute(query).scalars().all()

        logger.info("process_mapcat", num_mapcats=len(result))

        for res in result:
            needs_update = res.last_updated.astimezone(timezone.utc) + timedelta(hours=res.update_cadence_hours) < datetime.now(tz=timezone.utc)
            has_never_been_updated = res.mapcat_last_update_time is None
            logger.debug("process_mapcat.check_update", mapcat_id=res.id, needs_update=needs_update, has_never_been_updated=has_never_been_updated)
            if needs_update or has_never_been_updated:
                logger.info("process_mapcat.update", mapcat_id=res.id)
                res.update_mapcat(session=session)
                logger.info("process_mapcat.update_complete", mapcat_id=res.id)