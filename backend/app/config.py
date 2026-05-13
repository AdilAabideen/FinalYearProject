"""Config module helpers."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
from typing import Optional, Union
from dotenv import load_dotenv

load_dotenv()

_REPO_ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Emergency Severity Index Multi Agent V Monolithic Agent System"
    DEBUG: Union[bool, str] = False
    VERSION: str = "1.0.0"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///app.db"
    SQLALCHEMY_ECHO: Union[bool, str] = False


    # LLM / Agentic settings (LangChain / LangGraph)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None
    # Dr7 settings
    DR7_API_KEY: Optional[str] = None
    DR7_MEDICAL_BASE_URL: str = "https://dr7.ai/api/v1/medical"
    DR7_RATE_LIMIT_MAX_RETRIES: int = 2
    DR7_RATE_LIMIT_BACKOFF_INITIAL_S: float = 10.0
    DR7_RATE_LIMIT_BACKOFF_MULTIPLIER: float = 2.0
    DR7_RATE_LIMIT_BACKOFF_MAX_S: float = 40.0

    # Llama Server settings
    LLAMA_SERVER_BASE_URL: str = "https://aa4its07ztlqwx-8000.proxy.runpod.net/v1"
    # LLAMA_SERVER_BASE_URL: str = "http://localhost:8080/v1"
    LLAMA_SERVER_API_KEY: Optional[str] = None
    LLAMA_SERVER_SERIAL_REQUESTS: Union[bool, str] = False
    LLAMA_SERVER_TIMEOUT_S: float = 60.0

    # Agent runtime safety
    TEST_CASE_BACKOFF_S: float = 5.0
    MAS_TEST_CASE_BACKOFF_S: float = 20.0
    
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        case_sensitive=True,
        extra="ignore"  # Ignore extra env vars
    )
    
    @field_validator('DEBUG', mode='before')
    @classmethod
    def parse_debug(cls, v):
        """Parse debug."""
        # Keep the output consistent.
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False
    
    @field_validator('SQLALCHEMY_ECHO', mode='before')
    @classmethod
    def parse_echo(cls, v):
        """Parse echo."""
        # Keep the output consistent.
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False

    @field_validator('LLAMA_SERVER_SERIAL_REQUESTS', mode='before')
    @classmethod
    def parse_llama_serial_requests(cls, v):
        """Parse llama serial requests."""
        # Keep the output consistent.
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False

settings = Settings()
