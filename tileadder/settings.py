"""
Settings for the tileadder system
"""

from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # soauth setup
    auth_type: Literal["soauth", "mock"] = "mock"
    "The authentication type to use."

    app_id: UUID | None = None
    client_secret: str | None = None
    public_key: str | None = None
    key_pair_type: str = "Ed25519"

    authentication_base_url: str = "https://identity.simonsobservatory.org"
    app_base_url: str = "http://localhost:8000"

    app_id_filename: Path | None = None  # Suggest /data/app_id
    client_secret_filename: Path | None = None  # Suggest /data/client_secret
    public_key_filename: Path | None = None  # Suggest /data/public_key.pem

    database_url: str = "sqlite:///database.db"
    map_directory: Path = Path(
        "/Users/borrow-adm/Documents/Projects/tileadder/tileadder"
    )

    model_config = SettingsConfigDict(env_prefix="TILEADDER_", env_file=".env")

    @model_validator(mode="after")
    def load_keys_from_files(self):
        def maybe_read(path: Path | None):
            if path and path.exists():
                return path.read_text().strip()
            return None

        self.app_id = self.app_id or maybe_read(self.app_id_filename)
        self.client_secret = self.client_secret or maybe_read(
            self.client_secret_filename
        )
        self.public_key = self.public_key or maybe_read(self.public_key_filename)

        return self
