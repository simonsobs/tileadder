"""
Tools for templating. Copied over from soauth and made a bit simpler.
"""

from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Any, Annotated

from fastapi import Request, FastAPI, Depends
from fastapi.templating import Jinja2Templates
from structlog import get_logger
from structlog.types import FilteringBoundLogger


def setup_templating(
    template_directory: Path,
    available_strings: dict[str, str] | None = None,
    extra_functions: dict[str, Callable] | None = None,
    context_processors: Iterable[Callable] = (),
) -> Callable:
    """
    Set up the Jinja-based templating system. Returns a function for
    getting the templating system ready for use as a dependency.
    """

    def user_and_scope(request: Request):
        return {"user": request.user, "scopes": request.auth.scopes}

    def strings(r):
        return available_strings or {}

    def functions(r):
        return extra_functions or {}

    templates = Jinja2Templates(
        directory=template_directory,
        context_processors=[user_and_scope, strings, functions]
        + list(context_processors),
    )

    @lru_cache
    def get_templates():
        return templates

    return get_templates
    
def logger():
    return get_logger()
    
templates = setup_templating(
    template_directory=Path(__file__.replace("templating.py", "templates")),
)

LoggerDependency = Annotated[FilteringBoundLogger, Depends(logger)]
TemplateDependency = Annotated[Jinja2Templates, Depends(templates)]

def template_endpoint(
    app: FastAPI,
    path: str,
    template: str,
    context: dict[str, Any] = {},
    methods=["GET"],
    log_name: str | None = None,
):
    def core(request: Request, templates: TemplateDependency, log: LoggerDependency):
        if log_name is not None:
            log.bind(user=request.user, scopes=request.auth.scopes, context=context)
            log.info(log_name)
        return templates.TemplateResponse(
            request=request,
            name=template,
            context=context,
        )

    app.add_api_route(path=path, endpoint=core)