"""
API endpoints for adding new maps to the system.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tileadder.service.creation import (
    MapFormData,
    create_map_group,
    parse_map_form_to_orm,
)
from tileadder.service.existing import read_map_groups
from tileadder.service.filesystem import (
    safe_evaluate,
    safe_read_directory_specific_file_types,
)

from .templating import LoggerDependency, TemplateDependency, templateify

router = APIRouter(prefix="/add")


@router.get("")
@templateify(template_name="add.html", log_name="add.index")
def add_home(request: Request, log: LoggerDependency, templates: TemplateDependency):
    return


class PathPOSTRequest(BaseModel):
    path: Path | None = None


@router.post("/list")
@templateify(template_name="htmx/directory_listing.html", log_name="add.list")
def get_list(
    x: PathPOSTRequest,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    search_path = (
        request.app.map_directory / x.path if x.path else request.app.map_directory
    )
    files, directories = safe_read_directory_specific_file_types(
        request.app.map_directory, search_path
    )

    show_directory = (
        x.path is not None and x.path.absolute() != request.app.map_directory.absolute()
    )

    return {
        "files": files,
        "directories": directories,
        "requested_directory": x.path.relative_to(x.path.parent)
        if show_directory
        else None,
        "parent_directory": x.path.parent if show_directory else None,
    }


@router.post("/evaluate")
@templateify(template_name="htmx/evaluate.html", log_name="add.evaluate")
def evaluate(
    x: PathPOSTRequest,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    try:
        layers = safe_evaluate(
            top_level=request.app.map_directory,
            file_path=request.app.map_directory / x.path,
        )
    except OSError:
        raise HTTPException(500, "Error with FITS file")
    return {
        "filename": x.path.name,
        "path": x.path,
        "layers": layers,
        "band_id": layers[0].layer_id.replace("-0-", "-"),
    }


class GroupCreationRequest(BaseModel):
    name: str
    description: str
    grant: str | None


@router.post("/groups")
def new_group(x: GroupCreationRequest, request: Request):
    with request.app.engine.session as s:
        create_map_group(
            name=x.name, description=x.description, grant=x.grant, session=s
        )

    response = Response(content=None, status_code=201, headers={"HX-Refresh": "true"})

    return response


@router.get("/create")
@templateify(template_name="htmx/create_new_map.html", log_name="add.create_map_form")
def create_map_form(
    bandid: str,
    request: Request,
    log: LoggerDependency,
    templates: TemplateDependency,
):
    with request.app.engine.session as s:
        map_groups = read_map_groups(session=s)

    return {"map_groups": map_groups, "band_id": bandid}


@router.post("/create")
def create(x: MapFormData, request: Request):
    with request.app.engine.session as s:
        parse_map_form_to_orm(
            form=x,
            session=s,
            top_level=request.app.map_directory,
        )

    return HTMLResponse(f"<p>Created map {x.name} in group {x.map_group_id}.</p>")
