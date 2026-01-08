"""
Tools for looking at existing maps in the database.
"""

from collections import namedtuple

from sqlalchemy import select
from sqlalchemy.orm import Session
from tilemaker.metadata.database import MapGroupORM, MapORM

map_group = namedtuple("MapGroup", ("name", "id"))
map_item = namedtuple(
    "MapItem", ("name", "id", "map_id", "map_group_id", "description")
)


def read_map_group_names(session: Session) -> list[map_group]:
    """
    Read only the names of the map and their IDs
    """

    results = session.execute(select(MapGroupORM)).scalars().all()

    return [map_group(name=x.name, id=x.id) for x in results]


def read_maps_for_map_group(session: Session, map_group_id: int) -> list[map_item]:
    """
    Read the map item information for a specific map group.
    """

    results = (
        session.execute(select(MapORM).where(MapORM.map_group_id == map_group_id))
        .scalars()
        .all()
    )

    return [
        map_item(
            name=x.name,
            id=x.id,
            map_id=x.map_id,
            map_group_id=x.map_group_id,
            description=x.description,
        )
        for x in results
    ]
