"""
Base repository with generic CRUD operations.
All repositories inherit from this to get standard database operations.
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository with CRUD operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Get entity by ID.

        Args:
            id: Entity UUID

        Returns:
            Entity or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get all entities with pagination and optional filters.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            filters: Dictionary of field:value filters

        Returns:
            List of entities
        """
        query = self.db.query(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        return query.offset(skip).limit(limit).all()

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filters.

        Args:
            filters: Dictionary of field:value filters

        Returns:
            Count of matching entities
        """
        query = self.db.query(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        return query.count()

    def create(self, **kwargs) -> ModelType:
        """
        Create new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity
        """
        entity = self.model(**kwargs)
        self.db.add(entity)
        self.db.flush()  # Flush to get ID without committing transaction
        self.db.refresh(entity)
        return entity

    def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """
        Update entity by ID.

        Args:
            id: Entity UUID
            **kwargs: Fields to update

        Returns:
            Updated entity or None if not found
        """
        entity = self.get_by_id(id)
        if not entity:
            return None

        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, id: UUID) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(id)
        if not entity:
            return False

        self.db.delete(entity)
        self.db.flush()
        return True

    def exists(self, **filters) -> bool:
        """
        Check if entity exists with given filters.

        Args:
            **filters: Field:value pairs to filter by

        Returns:
            True if exists, False otherwise
        """
        query = self.db.query(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)

        return query.first() is not None

    def get_one(self, **filters) -> Optional[ModelType]:
        """
        Get single entity matching filters.

        Args:
            **filters: Field:value pairs to filter by

        Returns:
            Entity or None if not found
        """
        query = self.db.query(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)

        return query.first()

    def get_multi(self, **filters) -> List[ModelType]:
        """
        Get multiple entities matching filters.

        Args:
            **filters: Field:value pairs to filter by

        Returns:
            List of matching entities
        """
        query = self.db.query(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)

        return query.all()

    def commit(self) -> None:
        """Commit current transaction."""
        self.db.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.db.rollback()
