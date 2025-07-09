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
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "INSECURE_DEFAULT_CHANGE_IN_PRODUCTION")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "INSECURE_JWT_DEFAULT_CHANGE_IN_PRODUCTION")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = 8000
    API_DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/ai_error_translator")
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # CORS Configuration  
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    
    # AI Configuration
    MAX_CONTEXT_LENGTH: int = 4000
    
    # Frontend Configuration
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://errortranslator.com")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Monitoring Configuration
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8001"))
    
    # Error Tracking
    ENABLE_ERROR_TRACKING: bool = os.getenv("ENABLE_ERROR_TRACKING", "true").lower() == "true"
    ERROR_SAMPLE_RATE: float = float(os.getenv("ERROR_SAMPLE_RATE", "1.0"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()