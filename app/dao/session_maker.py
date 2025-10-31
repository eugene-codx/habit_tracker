from contextlib import asynccontextmanager
from functools import wraps
from collections.abc import AsyncGenerator, Callable

from fastapi import Depends
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.dao.database import async_session_maker


class DatabaseSessionManager:
    """
    Class for managing asynchronous database sessions, including transaction support and FastAPI dependencies.
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    @asynccontextmanager
    async def create_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create and provide a new database session.
        Ensures the session is closed after completion.
        """
        async with self.session_maker() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Error creating database session: {e}")
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def transaction(self, session: AsyncSession) -> AsyncGenerator[None, None]:
        """
        Transaction management: commit on success, rollback on error.
        """
        try:
            yield
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction error: {e}")
            raise

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency returning a session without transaction handling.
        """
        async with self.create_session() as session:
            yield session

    async def get_transaction_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency returning a session with transaction handling.
        """
        async with self.create_session() as session, self.transaction(session):
            yield session

    def connection(self, isolation_level: str | None = None, commit: bool = True):
        """
        Decorator for session management with optional isolation level and commit control.

        Parameters:
        - `isolation_level`: transaction isolation level (e.g. "SERIALIZABLE").
        - `commit`: if `True`, commit after method execution.
        """

        def decorator(method):
            @wraps(method)
            async def wrapper(*args, **kwargs):
                async with self.session_maker() as session:
                    try:
                        if isolation_level:
                            await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))

                        result = await method(*args, session=session, **kwargs)

                        if commit:
                            await session.commit()

                        return result
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Error during transaction execution: {e}")
                        raise
                    finally:
                        await session.close()

            return wrapper

        return decorator

    @property
    def session_dependency(self) -> Callable:
        """Return a FastAPI dependency that provides a session without a transaction."""
        return Depends(self.get_session)

    @property
    def transaction_session_dependency(self) -> Callable:
        """Return a FastAPI dependency with transaction support."""
        return Depends(self.get_transaction_session)


# Initialize database session manager
session_manager = DatabaseSessionManager(async_session_maker)

# FastAPI dependencies for using sessions
SessionDep = session_manager.session_dependency
TransactionSessionDep = session_manager.transaction_session_dependency

# Example of using the decorator
# @session_manager.connection(isolation_level="SERIALIZABLE", commit=True)
# async def example_method(*args, session: AsyncSession, **kwargs):
#     # Method logic
#     pass


# Example of using the dependency
# @router.post("/register/")
# async def register_user(user_data: SUserRegister, session: AsyncSession = TransactionSessionDep):
#     # Endpoint logic
#     pass
