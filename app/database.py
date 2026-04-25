from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import re

class Settings(BaseSettings):
    database_url: str
    api_key: str
    gemini_api_key: str = ""  # Google Gemini AI API key (optional)
    gemini_mode: str = "commentary"  # Options: 'disabled', 'commentary', 'prediction'
    prediction_mode: str = "advanced"  # Options: 'basic', 'ml', 'advanced'
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
    connect_args={"ssl": "require"}
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session