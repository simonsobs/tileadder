"""
Core 'frontend' app, where users can log in and view/update status.
This does not require any access to the database, and purely uses the
soauth authentication scheme. It is packed purely for simplicity.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from soauth.toolkit.fastapi import global_setup, mock_global_setup

from tileadder.settings import Settings

from .add import router as add_router
from .current import router as current_router
from .database import EngineManager
from .templating import template_endpoint

settings = Settings()

key_type = settings.key_pair_type

favicon = FileResponse(
    __file__.replace("app.py", "favicon.ico"), media_type="image/x-icon"
)
apple_touch = FileResponse(
    __file__.replace("app.py", "apple-touch-icon.png"), media_type="image/png"
)


async def lifespan(app: FastAPI):
    app.app_id = str(settings.app_id)
    app.engine = EngineManager(database_url=settings.database_url)
    app.map_directory = settings.map_directory
    yield


app = FastAPI(lifespan=lifespan)


if settings.auth_type == "soauth":
    app = global_setup(
        app=app,
        app_base_url=settings.app_base_url,
        authentication_base_url=settings.authentication_base_url,
        app_id=settings.app_id,
        client_secret=settings.client_secret,
        public_key=settings.public_key,
        key_pair_type=key_type,
    )
else:
    app = mock_global_setup(app, grants=["maps:add", "maps:edit", "maps:admin"])


template_endpoint(app=app, path="/", template="index.html", log_name="app.home")

app.include_router(router=current_router)
app.include_router(router=add_router)
