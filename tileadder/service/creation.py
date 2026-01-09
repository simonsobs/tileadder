"""
Tools for creating new database rows.
"""

from sqlalchemy.orm import Session
from tilemaker.metadata.database import MapGroupORM


def create_map_group(
    name: str, description: str, grant: str | None, session: Session
) -> MapGroupORM:
    new_map_group = MapGroupORM(name=name, description=description, grant=grant)
    session.add(new_map_group)
    session.commit()

    return new_map_group
