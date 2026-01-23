"""
Tools for creating new database rows.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session
from tilemaker.metadata.database import (
    BandORM,
    LayerORM,
    MapGroupORM,
    MapORM,
)

from tileadder.service.filesystem import safe_evaluate


def create_map_group(
    name: str, description: str, grant: str | None, session: Session
) -> MapGroupORM:
    new_map_group = MapGroupORM(name=name, description=description, grant=grant)
    session.add(new_map_group)
    session.commit()

    return new_map_group


class LayerData(BaseModel):
    layer_id: str = Field(..., description="Unique layer identifier")
    included: bool = Field(..., description="Whether the layer is included in the map")
    name: str | None = None
    description: str | None = None
    quantity: str | None = Field(
        None, description="Physical quantity represented (string to allow symbols)"
    )
    units: str | None = Field(None, description="Units of the quantity")
    vmin: float | Literal["auto"] = Field("auto", description='Minimum value or "auto"')
    vmax: float | Literal["auto"] = Field("auto", description='Maximum value or "auto"')
    cmap: str = Field("viridis", description="Matplotlib colormap name")


class BandFormData(BaseModel):
    band_id: str = Field(..., description="Band identifier")
    name: str = Field(..., description="Band name")
    description: str | None = None
    required_grant: str | None = None
    layers: list[LayerData] = Field(default_factory=list)
    path: Path


class MapFormData(BaseModel):
    name: str
    description: str
    map_group_id: int
    required_grant: str | None = None
    form_data: BandFormData


class ExistingMapFormData(BaseModel):
    map_id: str
    form_data: BandFormData


def parse_map_form_to_orm(
    form: MapFormData,
    session: Session,
    top_level: Path,
    extensions: tuple[str] = ("fits",),
) -> MapORM:
    # Re-parse from filesystem to grab base data.
    underlying_layers = safe_evaluate(
        top_level=top_level,
        file_path=top_level / form.form_data.path,
        extensions=extensions,
    )

    provider_adapter = TypeAdapter(type(underlying_layers[0].provider))

    layer_metadata = {
        x.layer_id: {
            "provider": provider_adapter.dump_python(x.provider, mode="json"),
            "bounding_left": x.bounding_left,
            "bounding_right": x.bounding_right,
            "bounding_top": x.bounding_top,
            "bounding_bottom": x.bounding_bottom,
            "number_of_levels": x.number_of_levels,
            "tile_size": x.tile_size,
        }
        for x in underlying_layers
    }

    try:
        layers = [
            LayerORM(
                layer_id=x.layer_id,
                name=x.name,
                description=x.description,
                grant=form.form_data.required_grant,
                quantity=x.quantity,
                units=x.units,
                vmin=x.vmin,
                vmax=x.vmax,
                cmap=x.cmap,
                **layer_metadata[x.layer_id],
            )
            for x in form.form_data.layers
            if x.included
        ]
    except KeyError:
        raise ValueError(
            f"Layers {[x.layer_id for x in form.form_data.layers]} not found in {form.form_data.path}"
        )

    band = BandORM(
        band_id=form.form_data.band_id,
        name=form.form_data.name,
        description=form.form_data.description,
        grant=form.form_data.required_grant,
        layers=layers,
    )

    map = MapORM(
        map_id=form.form_data.band_id[2:],
        name=form.name,
        description=form.description,
        grant=form.required_grant,
        map_group_id=form.map_group_id,
        bands=[band],
    )

    session.add(map)
    session.commit()

    return map


def parse_existing_map_to_orm(
    form: MapFormData,
    session: Session,
    top_level: Path,
    extensions: tuple[str] = ("fits",),
) -> MapORM:
    map = session.execute(
        select(MapORM).where(MapORM.map_id == form.map_id)
    ).scalar_one_or_none()

    if map is None:
        raise ValueError(f"Map with ID {form.map_id} does not exist")

    # We may have an existing band with that name. Let's do the smart thing
    # and upsert it.
    band = session.execute(
        select(BandORM).where(BandORM.name == form.form_data.name)
    ).scalar_one_or_none()

    if band is None:
        band = BandORM(
            band_id=form.form_data.band_id,
            name=form.form_data.name,
            description=form.form_data.description,
            grant=form.form_data.required_grant,
            layers=layers,
            map_id=map.id,
        )

    # Re-parse from filesystem to grab base data.
    underlying_layers = safe_evaluate(
        top_level=top_level,
        file_path=top_level / form.form_data.path,
        extensions=extensions,
    )

    provider_adapter = TypeAdapter(type(underlying_layers[0].provider))

    layer_metadata = {
        x.layer_id: {
            "provider": provider_adapter.dump_python(x.provider, mode="json"),
            "bounding_left": x.bounding_left,
            "bounding_right": x.bounding_right,
            "bounding_top": x.bounding_top,
            "bounding_bottom": x.bounding_bottom,
            "number_of_levels": x.number_of_levels,
            "tile_size": x.tile_size,
        }
        for x in underlying_layers
    }

    try:
        layers = [
            LayerORM(
                layer_id=x.layer_id,
                name=x.name,
                description=x.description,
                grant=band.grant,
                quantity=x.quantity,
                units=x.units,
                vmin=x.vmin,
                vmax=x.vmax,
                cmap=x.cmap,
                **layer_metadata[x.layer_id],
            )
            for x in form.form_data.layers
            if x.included
        ]
    except KeyError:
        raise ValueError(
            f"Layers {[x.layer_id for x in form.form_data.layers]} not found in {form.form_data.path}"
        )

    band.layers += layers

    session.add(band)
    session.commit()

    return map
