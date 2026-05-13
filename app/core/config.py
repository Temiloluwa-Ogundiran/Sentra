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
    squad_callback_url: str = ""
    openai_api_key: str = ""
    openai_orchestrator_model: str = "gpt-4o"
    hosted_artifact_reasoner_url: str = ""
    hosted_tamper_detector_url: str = ""
    hosted_synthetic_artifact_detector_url: str = ""
    readiness_require_hosted: bool = False
    recharge_amount_kobo: int = 500000
    recharge_credits_to_add: int = 20
    processing_progress_interval_seconds: int = 60
    typing_refresh_interval_seconds: int = 6
    hosted_inference_timeout_seconds: int = 90

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
