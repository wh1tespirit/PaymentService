from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common import settings

engine = create_async_engine(settings.DATABASE_URI)

Session = async_sessionmaker(engine)
