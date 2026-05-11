from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sentra"
    app_env: str = "development"
    database_url: str = "sqlite:///./sentra.db"
    storage_root: Path = Path("storage")
    gowa_base_url: str = "http://localhost:3000"
    gowa_basic_auth_user: str = ""
    gowa_basic_auth_password: str = ""
    gowa_device_id: str = ""
    squad_base_url: str = "https://sandbox-api-d.squadco.com"
    squad_secret_key: str = ""
    squad_public_key: str = ""
    hosted_artifact_reasoner_url: str = ""
    hosted_tamper_detector_url: str = ""
    hosted_synthetic_artifact_detector_url: str = ""
    readiness_require_hosted: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
