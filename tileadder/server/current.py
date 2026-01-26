"""
Handling for currently loaded maps
"""

from fastapi import APIRouter, Request, Response

from tileadder.service.existing import (
    MapGroupEdit,
    delete_band,
    delete_map,
    delete_map_group,
    read_bands_for_map,
    read_map,
    read_map_group,
    read_map_groups,
    read_maps_for_map_group,
    update_map_group,
)

from .templating import LoggerDependency, TemplateDependency, templateify

router = APIRouter(prefix="/current")


@router.get("")
@templateify(template_name="current.html", log_name="current.index")
def groups(request: Request, log: LoggerDependency, templates: TemplateDependency):
    with request.app.engine.session as s:
        map_groups = read_map_groups(session=s)

    return {"map_groups": map_groups}


@router.delete("/groups/{map_group_id}")
def delete_map_group_endpoint(
    map_group_id: int,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        delete_map_group(session=s, map_group_id=map_group_id)


@router.get("/groups/edit/{map_group_id}")
@templateify(template_name="htmx/edit_map_group.html", log_name="current.edit_form")
def get_group_edit_form(
    map_group_id: int,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        map_group = read_map_group(session=s, map_group_id=map_group_id)

    return {"map_group": map_group}


@router.post("/groups/edit/{map_group_id}")
def perform_edit_of_map_group(
    map_group_id: int,
    content: MapGroupEdit,
    request: Request,
) -> Response:
    with request.app.engine.session as s:
        update_map_group(session=s, map_group_id=map_group_id, edit=content)

    return Response(headers={"HX-Refresh": "true"})


@router.get("/maps/{map_group_id}")
@templateify(
    template_name="htmx/maps_from_map_group.html",
    log_name="current.maps_from_map_group",
)
def maps_from_map_group(
    map_group_id: int,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        map_group = read_map_group(session=s, map_group_id=map_group_id)
        maps = read_maps_for_map_group(session=s, map_group_id=map_group_id)

    return {"map_group": map_group, "maps": maps}


@router.delete("/maps/{map_id}")
def delete_map_endpoint(
    map_id: int,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        delete_map(session=s, map_id=map_id)


@router.get("/bands/{map_id}")
@templateify(
    template_name="htmx/bands_from_map.html",
    log_name="current.bands_from_map",
)
def bands_from_map(
    map_id: int,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        bands = read_bands_for_map(session=s, map_id=map_id)
        map = read_map(session=s, map_id=map_id)

    return {"map": map, "bands": bands}


@router.delete("/bands/{band_id}")
def delete_band_endpoint(
    band_id: int,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        delete_band(session=s, band_id=band_id)
