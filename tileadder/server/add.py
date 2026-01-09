"""
API endpoints for adding new maps to the system.
"""

from pathlib import Path

from fastapi import APIRouter, Request

from tileadder.service.filesystem import safe_read_directory_specific_file_types

from .templating import LoggerDependency, TemplateDependency, templateify

router = APIRouter(prefix="/add")


@router.get("")
@templateify(template_name="add.html", log_name="current.index")
def add_home(request: Request, log: LoggerDependency, templates: TemplateDependency):
    return safe_read_directory_specific_file_types(Path("/"), Path("."))
