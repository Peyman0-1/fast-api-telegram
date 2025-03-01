from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import os

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

engine = create_async_engine(
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@127.0.0.1:5432/{DB_NAME}"
)

SessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False)
