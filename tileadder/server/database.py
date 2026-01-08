"""
Tools for connecting to the database for tilemaker.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class EngineManager:
    _engine: Engine | None = None
    _sessionmaker: sessionmaker | None = None

    def __init__(self, database_url: str):
        self.database_url = database_url

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self.database_url)

        return self._engine

    @property
    def session(self) -> Session:
        if self._sessionmaker is None:
            self._sessionmaker = sessionmaker(bind=self.engine)

        return self._sessionmaker()
