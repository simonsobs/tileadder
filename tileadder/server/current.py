"""
Handling for currently loaded maps
"""

from fastapi import Request, APIRouter
from .templating import templateify, LoggerDependency, TemplateDependency

from tileadder.service.existing import read_map_group_names

router = APIRouter(prefix="/current")

@router.get("")
@templateify(template_name="current.html", log_name="current.index")
def groups(request: Request, log: LoggerDependency, templates: TemplateDependency):
	with request.app.engine.session as s:
		map_group_names = read_map_group_names(session=s)
		
	return {"map_group_names": map_group_names}
