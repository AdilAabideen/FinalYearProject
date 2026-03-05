from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Union

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Emergency Severity Index Multi Agent V Monolithic Agent System"
    DEBUG: Union[bool, str] = False
    VERSION: str = "1.0.0"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///app.db"
    SQLALCHEMY_ECHO: Union[bool, str] = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
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

settings = Settings()