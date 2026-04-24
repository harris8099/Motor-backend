from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings
import re

class Settings(BaseSettings):
    database_url: str
    api_key: str
    class Config:
        env_file = ".env"

settings = Settings()

# Fix driver prefix
if settings.database_url.startswith("postgres://"):
    settings.database_url = settings.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif settings.database_url.startswith("postgresql://"):
    settings.database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Strip ?sslmode=... — asyncpg rejects this parameter
settings.database_url = re.sub(r'[?&]sslmode=[^&]*', '', settings.database_url)
settings.database_url = re.sub(r'\?$', '', settings.database_url)  # remove trailing ?

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"ssl": "require"}  # asyncpg's equivalent of sslmode=require
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session