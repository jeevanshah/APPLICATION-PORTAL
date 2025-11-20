"""
Campus Repository
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import Campus
from app.repositories.base import BaseRepository


class CampusRepository(BaseRepository[Campus]):
    """Repository for campus operations."""

    def __init__(self, db: Session):
        super().__init__(Campus, db)

    def get_by_rto(self, rto_profile_id: UUID, active_only: bool = True) -> List[Campus]:
        """Get all campuses for an RTO."""
        query = self.db.query(Campus).filter(
            Campus.rto_profile_id == rto_profile_id,
            Campus.deleted_at.is_(None)
        )
        
        if active_only:
            query = query.filter(Campus.is_active == True)
        
        return query.order_by(Campus.name).all()

    def get_by_code(self, code: str, rto_profile_id: UUID) -> Optional[Campus]:
        """Get campus by code within an RTO."""
        return self.db.query(Campus).filter(
            Campus.code == code,
            Campus.rto_profile_id == rto_profile_id,
            Campus.deleted_at.is_(None)
        ).first()

    def soft_delete(self, campus_id: UUID) -> bool:
        """Soft delete a campus."""
        from datetime import datetime
        campus = self.get_by_id(campus_id)
        if campus:
            campus.deleted_at = datetime.utcnow()
            campus.is_active = False
            self.db.commit()
            return True
        return False
