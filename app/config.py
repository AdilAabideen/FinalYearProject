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

    # Neo4j settings
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: Optional[str] = "neo4j"
    NEO4J_PASSWORD: Optional[str] = None

    # LLM / Agentic settings (LangChain / LangGraph)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Dr7 settings
    DR7_API_KEY: Optional[str] = None
    DR7_MEDICAL_BASE_URL: str = "https://dr7.ai/api/v1/medical"

    # Agent runtime safety
    AGENT_RUN_TIMEOUT_S: float = 120.0

    #LangSmith settings
    # LANGSMITH_API_KEY: Optional[str] = None
    # LANGSMITH_PROJECT: Optional[str] = None
    # LANGCHAIN_TRACING_V2: Union[bool, str] = False
    
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        case_sensitive=True,
        extra="ignore"  # Ignore extra env vars
    )
    
    @field_validator('DEBUG', mode='before')
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False
    
    @field_validator('SQLALCHEMY_ECHO', mode='before')
    @classmethod
    def parse_echo(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False

    # @field_validator('LANGCHAIN_TRACING_V2', mode='before')
    # @classmethod
    # def parse_langchain_tracing(cls, v):
    #     if isinstance(v, bool):
    #         return v
    #     if isinstance(v, str):
    #         return v.lower() in ('true', '1', 'yes', 'on')
    #     return False

settings = Settings()
