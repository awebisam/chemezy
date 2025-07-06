from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database settings
    database_url: str = "sqlite:///./chemezy.db"

    # Security settings (REQUIRED for production)
    secret_key: str  # Must be set in environment - no default for security
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS settings
    # Add your Unity client domains
    allowed_origins: list[str] = ["http://localhost:3000"]

    # PubChem API settings
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    pubchem_timeout: int = 10

    # DSPy/LLM settings - Azure OpenAI
    azure_openai_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_name: Optional[str] = None
    azure_openai_model_name: str = "gpt-4o-mini"


    # Application settings
    app_name: str = "Chemezy Backend Engine"
    debug: bool = False

    # Rate limiting (optional - for future enhancement)
    redis_url: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
