import uuid
from typing import Any, Generic, TypeVar

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import delete as sqlalchemy_delete, func, update as sqlalchemy_update, or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .database import Base

# Declare type parameter T constrained to subclasses of Base
T = TypeVar("T", bound=Base)


class BaseDAO(Generic[T]):
    """
    Base DAO class for asynchronous work with SQLAlchemy models.
    Provides common methods for searching, adding, updating, deleting,
    counting and paginating records.
    """

    model: type[T]

    @classmethod
    async def find_one_or_none_by_id(cls, data_id: int, session: AsyncSession):
        """
        Find a record by its ID.
        :param data_id: record ID
        :param session: SQLAlchemy async session
        :return: model instance or None
        """
        logger.info(f"Searching for {cls.model.__name__} with ID: {data_id}")
        try:
            query = select(cls.model).filter_by(id=data_id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            if record:
                logger.info(f"Record with ID {data_id} found.")
            else:
                logger.info(f"Record with ID {data_id} not found.")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Error while searching for record with ID {data_id}: {e}")
            raise

    @classmethod
    async def find_one_or_none_by_public_id(cls, data_public_id: uuid.UUID, session: AsyncSession):
        """
        Find a record by its PUBLIC_ID.
        :param data_public_id: record PUBLIC_ID
        :param session: SQLAlchemy async session
        :return: model instance or None
        """
        logger.info(f"Searching for {cls.model.__name__} with PUBLIC_ID: {data_public_id}")
        try:
            query = select(cls.model).filter_by(public_id=data_public_id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            if record:
                logger.info(f"Record with PUBLIC_ID {data_public_id} found.")
            else:
                logger.info(f"Record with PUBLIC_ID {data_public_id} not found.")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Error while searching for record with PUBLIC_ID {data_public_id}: {e}")
            raise

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, filters: dict | list[dict[str, Any]]):
        """
        Find a single record by filters.
        :param session: SQLAlchemy async session
        :param filters: filter dictionary or list of filter dictionaries (combined with OR)
        :return: model instance or None
        """
        logger.info(f"Searching one {cls.model.__name__} by filters: {filters}")
        try:
            if isinstance(filters, list):
                conditions = [and_(*[getattr(cls.model, k) == v for k, v in f.items()]) for f in filters]
                query = select(cls.model).filter(or_(*conditions))
            else:
                query = select(cls.model).filter_by(**filters)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            if record:
                logger.info(f"Record found by filters: {filters}")
            else:
                logger.info(f"Record not found by filters: {filters}")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Error while searching record by filters {filters}: {e}")
            raise

    @classmethod
    async def find_all(cls, session: AsyncSession, filters: BaseModel | None):
        """
        Find all records by filters.
        :param session: SQLAlchemy async session
        :param filters: Pydantic model with filters or None
        :return: list of model instances
        """
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}

        logger.info(f"Searching all {cls.model.__name__} by filters: {filter_dict}")
        try:
            query = select(cls.model).filter_by(**filter_dict)
            result = await session.execute(query)
            records = result.scalars().all()
            logger.info(f"Found {len(records)} records.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error while searching all records by filters {filter_dict}: {e}")
            raise

    @classmethod
    async def add(cls, session: AsyncSession, values: BaseModel):
        """
        Add a single record.
        :param session: SQLAlchemy async session
        :param values: Pydantic model with creation data
        :return: created model instance
        """
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f"Adding {cls.model.__name__} with parameters: {values_dict}")
        new_instance = cls.model(**values_dict)
        session.add(new_instance)
        try:
            await session.flush()
            logger.info(f"{cls.model.__name__} added successfully.")
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error while adding record: {e}")
            raise e
        return new_instance

    @classmethod
    async def add_many(cls, session: AsyncSession, instances: list[BaseModel]):
        """
        Add multiple records.
        :param session: SQLAlchemy async session
        :param instances: list of Pydantic models with creation data
        :return: list of created model instances
        """
        values_list = [item.model_dump(exclude_unset=True) for item in instances]
        logger.info(f"Adding multiple {cls.model.__name__} records. Count: {len(values_list)}")
        new_instances = [cls.model(**values) for values in values_list]
        session.add_all(new_instances)
        try:
            await session.flush()
            logger.info(f"Successfully added {len(new_instances)} records.")
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error while adding multiple records: {e}")
            raise e
        return new_instances

    @classmethod
    async def update(cls, session: AsyncSession, filters: BaseModel, values: BaseModel):
        """
        Update records by filters.
        :param session: SQLAlchemy async session
        :param filters: Pydantic model with filters
        :param values: Pydantic model with new values
        :return: number of updated records
        """
        filter_dict = filters.model_dump(exclude_unset=True)
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f"Updating {cls.model.__name__} records by filter: {filter_dict} with params: {values_dict}")
        query = (
            sqlalchemy_update(cls.model)
            .where(*[getattr(cls.model, k) == v for k, v in filter_dict.items()])
            .values(**values_dict)
            .execution_options(synchronize_session="fetch")
        )
        try:
            result = await session.execute(query)
            await session.flush()
            logger.info(f"Updated {result.rowcount} records.")
            return result.rowcount
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error while updating records: {e}")
            raise e

    @classmethod
    async def delete(cls, session: AsyncSession, filters: BaseModel):
        """
        Delete records by filter.
        :param session: SQLAlchemy async session
        :param filters: Pydantic model with filters
        :return: number of deleted records
        """
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f"Deleting {cls.model.__name__} records by filter: {filter_dict}")
        if not filter_dict:
            logger.error("At least one filter is required for deletion.")
            raise ValueError("At least one filter is required for deletion.")

        query = sqlalchemy_delete(cls.model).filter_by(**filter_dict)
        try:
            result = await session.execute(query)
            await session.flush()
            logger.info(f"Deleted {result.rowcount} records.")
            return result.rowcount
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error while deleting records: {e}")
            raise e

    @classmethod
    async def count(cls, session: AsyncSession, filters: BaseModel):
        """
        Count records by filter.
        :param session: SQLAlchemy async session
        :param filters: Pydantic model with filters
        :return: number of records
        """
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f"Counting {cls.model.__name__} records by filter: {filter_dict}")
        try:
            query = select(func.count(cls.model.id)).filter_by(**filter_dict)
            result = await session.execute(query)
            count = result.scalar()
            logger.info(f"Found {count} records.")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error while counting records: {e}")
            raise

    @classmethod
    async def paginate(cls, session: AsyncSession, page: int = 1, page_size: int = 10, filters: BaseModel = None):
        """
        Get records with pagination.
        :param session: SQLAlchemy async session
        :param page: page number
        :param page_size: page size
        :param filters: Pydantic model with filters
        :return: list of model instances on the page
        """
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Paginating {cls.model.__name__} by filter: {filter_dict}, page: {page}, page size: {page_size}")
        try:
            query = select(cls.model).filter_by(**filter_dict)
            result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
            records = result.scalars().all()
            logger.info(f"Found {len(records)} records on page {page}.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error while paginating records: {e}")
            raise

    @classmethod
    async def find_by_ids(cls, session: AsyncSession, ids: list[int]) -> list[Any]:
        """
        Find multiple records by a list of IDs.
        :param session: SQLAlchemy async session
        :param ids: list of IDs
        :return: list of model instances
        """
        logger.info(f"Searching {cls.model.__name__} records by ID list: {ids}")
        try:
            query = select(cls.model).filter(cls.model.id.in_(ids))
            result = await session.execute(query)
            records = result.scalars().all()
            logger.info(f"Found {len(records)} records by ID list.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error while searching records by ID list: {e}")
            raise

    @classmethod
    async def upsert(cls, session: AsyncSession, unique_fields: list[str], values: BaseModel):
        """
        Create a record or update an existing one by unique fields.
        :param session: SQLAlchemy async session
        :param unique_fields: list of unique fields
        :param values: Pydantic model with data
        :return: created or updated model instance
        """
        values_dict = values.model_dump(exclude_unset=True)
        filter_dict = {field: values_dict[field] for field in unique_fields if field in values_dict}

        logger.info(f"Upsert for {cls.model.__name__}")
        try:
            existing = await cls.find_one_or_none(session, filter_dict)
            if existing:
                # Update existing record
                for key, value in values_dict.items():
                    setattr(existing, key, value)
                await session.flush()
                logger.info(f"Existing {cls.model.__name__} record updated")
                return existing
            else:
                # Create new record
                new_instance = cls.model(**values_dict)
                session.add(new_instance)
                await session.flush()
                logger.info(f"New {cls.model.__name__} record created")
                return new_instance
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error during upsert: {e}")
            raise

    @classmethod
    async def bulk_update(cls, session: AsyncSession, records: list[BaseModel]) -> int:
        """
        Bulk update records by their ID.
        :param session: SQLAlchemy async session
        :param records: list of Pydantic models with updated data (must contain an id field)
        :return: number of updated records
        """
        logger.info(f"Bulk updating {cls.model.__name__} records")
        try:
            updated_count = 0
            for record in records:
                record_dict = record.model_dump(exclude_unset=True)
                if "id" not in record_dict:
                    continue

                update_data = {k: v for k, v in record_dict.items() if k != "id"}
                stmt = sqlalchemy_update(cls.model).filter_by(id=record_dict["id"]).values(**update_data)
                result = await session.execute(stmt)
                updated_count += result.rowcount

            await session.flush()
            logger.info(f"Updated {updated_count} records")
            return updated_count
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error during bulk update: {e}")
            raise
