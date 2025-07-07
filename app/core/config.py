from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    database_url: str = "postgresql://chemezy:chemezy@localhost/chemezy"
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # PubChem API settings
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    pubchem_timeout: int = 10
    
    # DSPy/LLM settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # Application settings
    app_name: str = "Chemezy Backend Engine"
    debug: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings()