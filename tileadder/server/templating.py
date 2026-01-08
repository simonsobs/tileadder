"""
Tools for templating. Copied over from soauth and made a bit simpler.
"""

from functools import lru_cache, wraps
from pathlib import Path
from typing import Annotated, Any, Callable, Iterable

from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates
from structlog import get_logger
from structlog.types import FilteringBoundLogger
from tileadder.settings import Settings

settings = Settings()

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
    available_strings={
        "base_url": settings.app_base_url
    }
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


def templateify(template_name: str | None = None, log_name: str | None = None):
    """
    Apply a template to a route. Your route should return a dictionary
    which is added to the template context. You must have `request: Request`
    and `templates: TemplateDependency` in your kwargs. If log_name is not
    None, you must also have `log: LoggerDependency`.
    """

    def decorator(route: Callable):
        @wraps(route)
        def wrapped(*args, **kwargs):
            context = route(*args, **kwargs)

            if context is None:
                context = {}

            request = kwargs.get("request")
            templates: Jinja2Templates = kwargs.get("templates")

            if log_name is not None:
                log = kwargs.get("log")
                log = log.bind(
                    user=request.user, scopes=request.auth.scopes, context=context
                )
                log.info(log_name)

            return templates.TemplateResponse(
                request=request,
                name=template_name,
                context=context,
            )

        return wrapped

    return decorator
