"""
Integration with the mapcat library.
"""

import os
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from typing import Sequence

from mapcat.database import (
    DepthOneMapTable,
)
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
    text,
)
from sqlalchemy.orm import Session, relationship
from tilemaker.metadata.generation import filename_to_id
from tilemaker.metadata.orm import BandORM, Base, LayerORM, MapGroupORM, MapORM

from tileadder.service.filesystem import parse_layer_metadata

MAP_ATTRIBUTES_TO_USE = [
    (0, "map_path", "Map"),
    (1, "ivar_path", "IVar"),
    (2, "rho_path", "ρ"),
    (3, "kappa_path", "κ"),
    (4, "flux_path", "F"),
    (5, "snr_path", "S/N"),
    (6, "start_time_path", "Time (start)"),
    (7, "mean_time_path", "Time (mean)"),
    (8, "end_time_path", "Time (end)"),
]


def parse_depth_one_map(
    depth_one_map: DepthOneMapTable,
    depth_one_parent: str | Path,
    map_group_id: int,
    prefix: str,
    grant: str,
    existing_maps: dict[str, MapORM],
) -> MapORM:
    """
    Parse a DepthOneMapTable object into a MapORM object.

    Parameters
    ----------
    map_group_id : int
        The ID of the map group to which this map belongs.
    prefix : str
        The prefix to use for the map ID. This is the ID of the map group.
    grant : str
        The grant to use for the map.
    depth_one_map : DepthOneMapTable
        The DepthOneMapTable object to parse.
    existing_maps : dict[str, MapORM]
        A dictionary of existing maps, keyed by their map_id. This is used to avoid
        creating duplicate maps as 'maps' are sorted into maps by their central date.
    """

    map_central_time = datetime.fromtimestamp(depth_one_map.ctime, tz=timezone.utc)
    map_start_time = (
        datetime.fromtimestamp(depth_one_map.start_time, tz=timezone.utc)
        if depth_one_map.start_time is not None
        else None
    )
    map_end_time = (
        datetime.fromtimestamp(depth_one_map.stop_time, tz=timezone.utc)
        if depth_one_map.stop_time is not None
        else None
    )

    map_name = map_central_time.strftime("%Y-%m-%d")
    map_description = (
        f"Maps with central time on date {map_central_time.strftime('%Y-%m-%d')}"
    )

    map_id = f"{prefix}-{filename_to_id(map_name)}"

    if map_id not in existing_maps:
        existing_maps[map_id] = MapORM(
            map_id=map_id,
            name=map_name,
            description=map_description,
            grant=grant,
            map_group_id=map_group_id,
        )

    map_orm = existing_maps.get(map_id)

    band_name = f"{depth_one_map.tube_slot}"

    if map_start_time is not None and map_end_time is not None:
        time_start = map_start_time.strftime("%H:%M")
        time_end = map_end_time.strftime("%H:%M")

        start_date_offset = (map_start_time.date() - map_central_time.date()).days
        end_date_offset = (map_end_time.date() - map_central_time.date()).days

        if start_date_offset != 0:
            time_start = f"{time_start} ({'+' if start_date_offset > 0 else ''}{start_date_offset})"
        if end_date_offset != 0:
            time_end = (
                f"{time_end} ({'+' if end_date_offset > 0 else ''}{end_date_offset})"
            )

        band_name = f"{band_name} ({time_start} - {time_end})"

    band_orm = None

    for band in map_orm.bands:
        if band.name == band_name:
            band_orm = band
            break

    if band_orm is None:
        band_id = f"{map_orm.map_id}-{filename_to_id(band_name)}"

        band_orm = BandORM(
            name=band_name,
            band_id=band_id,
            description=f"Band for tube slot {depth_one_map.tube_slot} from {map_start_time} to {map_end_time}",
            grant=grant,
            map_id=map_orm.map_id,
        )
        map_orm.bands.append(band_orm)

    band_existing_layers = set(x.layer_id for x in band_orm.layers)

    for _, attribute_name, attribute_description in MAP_ATTRIBUTES_TO_USE:
        attribute_path = getattr(depth_one_map, attribute_name, None)

        if attribute_path is None:
            continue

        layer_id = f"{band_orm.band_id}-{filename_to_id(attribute_path)}-{filename_to_id(attribute_description)}"

        if layer_id in band_existing_layers:
            continue

        if attribute_path is not None:
            layers = parse_layer_metadata(
                top_level=Path(depth_one_parent),
                file_path=Path(attribute_path),
                extensions=("fits",),
            )
            for layer in layers.values():
                layer_orm = LayerORM(
                    layer_id=layer_id,
                    name=attribute_description,
                    description=f"{attribute_description} layer for band {band_orm.name}",
                    grant=grant,
                    band_id=band_orm.id,
                    **layer,
                )
                band_orm.layers.append(layer_orm)

    return map_orm


class MapCatRegistration(Base):
    __tablename__ = "mapcat_registration"

    id = Column(Integer, primary_key=True)

    time_added = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    added_by = Column(String, nullable=False)
    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    update_cadence_hours = Column(Integer, nullable=False, default=24)

    # Path to the mapcat itself
    mapcat_path = Column(String, nullable=False)
    # Type of mapcat database
    mapcat_database_type = Column(String, nullable=False)
    # Path to the root of the data that mapcat represents.
    mapcat_data_root = Column(String, nullable=False)
    # Datetime at which the mapcat was last changed
    mapcat_last_update_time = Column(DateTime, nullable=True)

    # The in SELECT * FROM $map_type WHERE $query
    query = Column(String, nullable=False)

    # The map type to query
    map_type = Column(String, nullable=False)

    # Linking to the _tilemaker_ database. Note that this is not map_group_id, which is
    # actually a string... TODO: Check whether we can combine those two.
    map_group_id = Column(
        Integer, ForeignKey("map_groups.id", ondelete="CASCADE"), nullable=False
    )
    map_group = relationship(
        "MapGroupORM", passive_deletes=True
    )

    @classmethod
    def create(
        cls,
        session: Session,
        map_group_name: str,
        map_group_description: str,
        grant: str,
        added_by: str,
        mapcat_path: str,
        mapcat_data_root: str,
        query: str,
        map_type: str = "depth_one_maps",
        update_cadence_hours: int = 24,
        mapcat_database_type: str = "sqlite",
    ):
        """
        Create a new MapCatRegistration object and add it to the tilemaker
        database. Requires a session to the tilemaker database.
        """

        map_group_orm = MapGroupORM(
            map_group_id=f"mapcat-{filename_to_id(map_group_name)}",
            name=map_group_name,
            description=map_group_description,
            grant=grant,
        )

        mapcat_registration = cls(
            added_by=added_by,
            update_cadence_hours=update_cadence_hours,
            mapcat_path=mapcat_path,
            mapcat_database_type=mapcat_database_type,
            mapcat_data_root=mapcat_data_root,
            mapcat_last_update_time=None,
            query=query,
            map_type=map_type,
            map_group=map_group_orm,
            map_group_id=map_group_orm.map_group_id,
        )

        session.add(mapcat_registration)
        session.commit()

        return mapcat_registration

    @cached_property
    def mapcat_settings(self):
        from mapcat.helper import Settings

        return Settings(
            database_name=self.mapcat_path,
            database_type=self.mapcat_database_type,
            depth_one_coadd_parent=self.mapcat_data_root,
            depth_one_parent=self.mapcat_data_root,
            atomic_coadd_parent=self.mapcat_data_root,
            atomic_parent=self.mapcat_data_root,
        )

    def update_mapcat(self, session: Session):
        """
        Update the mapcat by re-parsing it and updating the database
        if necessary. Requires a tilemaker database session.
        """

        self.last_updated = datetime.now(timezone.utc)

        if self.mapcat_last_update_time is not None:
            last_update_time = datetime.fromtimestamp(
                os.stat(self.mapcat_path).st_mtime
            )

            if last_update_time == self.mapcat_last_update_time:
                session.add(self)
                session.commit()
                return

        session.add(self)
        self.parse_mapcat(session=session)

        return

    def parse_mapcat(self, session: Session) -> Sequence[MapORM]:
        """
        Parse the mapcat and return a list of MapORM objects. Requires
        a session from the tilemaker database.
        """

        formulated_query = f"SELECT * FROM {self.map_type} WHERE {self.query};"
        expected_return_type = {
            "depth_one_maps": DepthOneMapTable,
            # TODO: Support non-depth-one maps.
            # "depth_one_coadds": DepthOneCoaddTable,
            # "atomic_maps": AtomicMapTable,
            # "atomic_coadds": AtomicCoaddTable,
        }

        if self.map_type not in expected_return_type:
            raise ValueError(f"Unknown map type: {self.map_type}")

        with self.mapcat_settings.session() as mapcat_session:
            print(formulated_query)
            query = select(expected_return_type[self.map_type]).from_statement(
                text(formulated_query)
            )
            result = mapcat_session.scalars(query)

            existing_maps = {map.map_id: map for map in self.map_group.maps}

            for map in result:
                parse_depth_one_map(
                    depth_one_map=map,
                    depth_one_parent=self.mapcat_settings.depth_one_parent,
                    map_group_id=self.map_group_id,
                    prefix=self.map_group.name,
                    grant=self.map_group.grant,
                    existing_maps=existing_maps,
                )

            session.add(*existing_maps.values())
            session.commit()

        return list(existing_maps.values())


class MapCatRegistrationFormData(BaseModel):
    map_group_name: str = Field(..., description="Name of the tilemaker map group")
    map_group_description: str = Field(
        ..., description="Description of the tilemaker map group"
    )
    grant: str | None = Field(None, description="Required grant for the map group")
    mapcat_path: str = Field(..., description="Path to the mapcat database")
    mapcat_database_type: str = Field(
        "sqlite", description="Type of mapcat database"
    )
    mapcat_data_root: str = Field(
        ..., description="Path to the root of the data represented by the mapcat"
    )
    query: str = Field(..., description="SQL WHERE clause used to select rows")
    map_type: str = Field("depth_one_maps", description="Mapcat table to query")
    update_cadence_hours: int = Field(
        24, ge=1, description="How often to refresh the registration"
    )


def create_mapcat_registration(
    form: MapCatRegistrationFormData,
    session: Session,
    added_by: str,
) -> MapCatRegistration:
    """
    Create a new MapCat registration and persist it.
    """

    return MapCatRegistration.create(
        session=session,
        map_group_name=form.map_group_name,
        map_group_description=form.map_group_description,
        grant=form.grant or "",
        added_by=added_by,
        mapcat_path=form.mapcat_path,
        mapcat_data_root=form.mapcat_data_root,
        query=form.query,
        map_type=form.map_type,
        update_cadence_hours=form.update_cadence_hours,
        mapcat_database_type=form.mapcat_database_type,
    )
