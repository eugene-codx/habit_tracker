from datetime import datetime
from typing import Any

from sqlalchemy import func, Integer, TIMESTAMP
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncAttrs, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column

from app.config import database_url

# Create asynchronous engine and session factory
engine = create_async_engine(url=database_url)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    # Define table columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @declared_attr
    def __tablename__(cls) -> str:
        # Automatic table name generation
        return cls.__name__.lower() + "s"

    def to_dict(self) -> dict[str, Any]:
        # Serialize object to a dictionary
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        """String representation of the object for easier debugging."""
        return f"<{self.__class__.__name__}(id={self.id}, created_at={self.created_at}, updated_at={self.updated_at})>"
