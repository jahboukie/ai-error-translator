import os
from typing import List
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # AI Service Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Stripe Configuration
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Model Tier Configuration
    FREE_TIER_MODEL: str = "gemini-1.5-flash"
    PRO_TIER_MODEL: str = "gemini-1.5-flash"
    
    # API Configuration
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "default-secret-key-change-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production-must-be-long-and-secure")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = 8000
    API_DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    
    # Database Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # CORS Configuration  
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # AI Configuration
    MAX_CONTEXT_LENGTH: int = 4000
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()