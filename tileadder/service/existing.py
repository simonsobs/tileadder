"""
Tools for looking at existing maps in the database.
"""

from collections import namedtuple

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from tilemaker.metadata.database import BandORM, MapGroupORM, MapORM

map_group = namedtuple("MapGroup", ("name", "id", "grant"))
map_item = namedtuple(
    "MapItem", ("name", "id", "map_id", "map_group_id", "description", "grant")
)
band_item = namedtuple(
    "BandItem", ("name", "id", "band_id", "map_id", "description", "grant", "layers")
)
layer_item = namedtuple(
    "LayerItem",
    (
        "name",
        "id",
        "layer_id",
        "band_id",
        "description",
        "grant",
        "quantity",
        "units",
        "number_of_levels",
        "tile_size",
    ),
)


def read_map_groups(session: Session) -> list[map_group]:
    """
    Read only the names of the map and their IDs
    """

    results = session.execute(select(MapGroupORM)).scalars().all()

    return [map_group(name=x.name, id=x.id, grant=x.grant) for x in results]


def read_map_group(session: Session, map_group_id: int) -> map_group:
    """
    Read a single map group
    """

    result = session.execute(
        select(MapGroupORM).where(MapGroupORM.id == map_group_id)
    ).scalar_one_or_none()

    if result is None:
        raise ValueError(f"Map group with id={map_group_id} not found")

    return map_group(name=result.name, id=result.id, grant=result.grant)


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
            grant=x.grant,
        )
        for x in results
    ]


def read_map(session: Session, map_id: int) -> map_group:
    """
    Read a single map group
    """

    result = session.execute(
        select(MapORM).where(MapORM.id == map_id)
    ).scalar_one_or_none()

    if result is None:
        raise ValueError(f"Map with id={map_id} not found")

    return map_item(
        name=result.name,
        id=result.id,
        map_id=result.map_id,
        map_group_id=result.map_group_id,
        description=result.description,
        grant=result.grant,
    )


def read_bands_for_map(session: Session, map_id: int) -> list[band_item]:
    """
    Read the band information for a specific map.
    """

    results = (
        session.execute(select(BandORM).where(BandORM.map_id == map_id)).scalars().all()
    )

    return [
        band_item(
            name=x.name,
            id=x.id,
            band_id=x.band_id,
            map_id=x.map_id,
            description=x.description,
            grant=x.grant,
            layers=[
                layer_item(
                    name=y.name,
                    id=y.id,
                    layer_id=y.layer_id,
                    band_id=y.band_id,
                    description=y.description,
                    grant=y.grant,
                    quantity=y.quantity,
                    units=y.units,
                    number_of_levels=y.number_of_levels,
                    tile_size=y.tile_size,
                )
                for y in x.layers
            ],
        )
        for x in results
    ]


class MapGroupEdit(BaseModel):
    group_name: str
    description: str | None
    grant: str | None


def update_map_group(session: Session, map_group_id: int, edit: MapGroupEdit):
    map_group = session.get(MapGroupORM, map_group_id)

    map_group.name = edit.group_name
    map_group.description = edit.description
    map_group.grant = edit.grant

    session.add(map_group)
    session.commit()


class MapEdit(BaseModel):
    map_name: str
    description: str | None
    grant: str | None


def update_map(session: Session, map_id: int, edit: MapEdit):
    map = session.get(MapORM, map_id)

    map.name = edit.map_name
    map.description = edit.description
    map.grant = edit.grant

    for band in map.bands:
        band.grant = edit.grant
        for layer in band.layers:
            layer.grant = edit.grant
            session.add(layer)
        session.add(band)
    session.add(map)

    session.commit()


def delete_map_group(session: Session, map_group_id: int):
    data = session.execute(
        select(MapGroupORM).where(MapGroupORM.id == map_group_id)
    ).scalar_one_or_none()
    session.delete(data)
    session.commit()

    return


def delete_map(session: Session, map_id: int):
    data = session.execute(
        select(MapORM).where(MapORM.id == map_id)
    ).scalar_one_or_none()
    session.delete(data)
    session.commit()

    return


def delete_band(session: Session, band_id: int):
    data = session.execute(
        select(BandORM).where(BandORM.id == band_id)
    ).scalar_one_or_none()
    session.delete(data)
    session.commit()

    return
