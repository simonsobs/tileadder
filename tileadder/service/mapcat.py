"""
Integration with the mapcat library.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from mapcat.database import DepthOneMapTable
from sqlalchemy import select
from sqlalchemy.orm import Session
from tilemaker.metadata.orm import LayerORM, BandORM, MapORM

from tileadder.service.filesystem import parse_layer_metadata

AVAILABLE_MAP_TYPES = {
    "map",
    "ivar",
    "mean_time",
    "rho",
    "kappa",
    "start_time",
    "end_time",
}


def perform_map_search(
    session: Session,
    start_time: datetime | None,
    end_time: datetime | None,
    frequency: str | None,
    tube_slot: str | None,
) -> Sequence[DepthOneMapTable]:
    """
    Perform a query against the mapcat.
    """
    query = select(DepthOneMapTable)

    if start_time:
        query = query.where(DepthOneMapTable.start_time > start_time)
    if end_time:
        query = query.where(DepthOneMapTable.end_time < end_time)
    if frequency:
        query = query.where(DepthOneMapTable.frequency == frequency)
    if tube_slot:
        query = query.where(DepthOneMapTable.tube_slot == tube_slot)

    results = session.execute(query).scalars().all()

    return results


def convert_map_cat_to_viewer_model(
    session: Session,
    top_level: Path,
    input: DepthOneMapTable,
    grant: str,
    date_format_string: str = "%Y-%m-%d %H:%M",
    map_name_format_string: str = "{date}",
    band_name_format_string: str = "{tube_slot}",
    layer_name_format_string: str = "{frequency} {map_type}",
):
    """
    Note that this session is into the main metadata database.
    The "map" corresponds to an observation period.
    The "band" corresponds to a specific tube_slot.
    The "layers" correspond to specific frequencies and the underlying maps.
    """

    date = datetime.fromtimestamp(input.ctime, tz=timezone.utc).strftime(
        date_format_string
    )

    available_format_strings = {
        "date": date,
        "tube_slot": input.tube_slot,
        "frequency": input.frequency,
    }

    map_name = map_name_format_string.format(**available_format_strings)
    band_name = band_name_format_string.format(**available_format_strings)
    
    if not (band := session.execute(select(BandORM).filter_by(name=band_name)).one_or_none()):
        band = BandORM(
            name=band_name,
            description="Depth one maps ingested from map catalog",
            grant=grant,
            layers=[]
        )

    for map_type in AVAILABLE_MAP_TYPES:
        band = BandORM(
        )
        if path := getattr(input, f"{map_type}_path", None):
            layer_metadata = parse_layer_metadata(top_level=top_level, file_path=path)

            if len(layer_metadata) > 0:
                raise ValueError("Depth one ingestion cannot handle multi-layer maps")

            layer_id = list(layer_metadata.keys())[0]
            lm = layer_metadata[layer_id]

            layer = LayerORM(
                layer_id=layer_id,
                name=layer_name_format_string.format(
                    map_type=map_type, **available_format_strings
                ),
                description="Depth one map ingested from map catalog",  # TODO: Improve this description with more metadata
                grant=grant,
                **lm,
            )
            
            band.layers.append(layer)
        
