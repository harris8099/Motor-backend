from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import re

class Settings(BaseSettings):
    database_url: str
    api_key: str
    gemini_api_key: str = ""  # Google Gemini AI API key (optional)
    mistral_api_key: str = "" # Mistral AI API key (optional)
    groq_api_key: str = ""    # Groq API key (optional)
    gemini_mode: str = "commentary"  # Options: 'disabled', 'commentary', 'prediction'
    prediction_mode: str = "advanced"  # Options: 'basic', 'ml', 'advanced'
    prediction_dispatch_mode: str = "auto"  # Options: 'auto', 'background', 'redis'
    redis_url: str = ""
    prediction_queue_name: str = "prediction_jobs"
    prediction_worker_block_seconds: int = 5
    # Set to your Vercel URL in production, e.g. https://your-app.vercel.app
    frontend_url: str = "*"
    jwt_secret: str = "change-me-in-production"  # JWT secret for auth tokens
    class Config:
        env_file = ".env"

settings = Settings()

# Fix driver prefix
url = settings.database_url
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Strip the ENTIRE query string — asyncpg doesn't accept any of these params
# (sslmode, channel_binding, etc.) — SSL is handled via connect_args instead
url = url.split("?")[0]

engine = create_async_engine(
    url,
    echo=False,
    connect_args={
        "ssl": "require",
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
    pool_pre_ping=True,     # test connection before use, discard stale ones
    pool_recycle=300,       # recycle connections every 5 min (before DB idle timeout)
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
