"""
Agent profile repository.
Handles agent-specific data operations.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload

from app.models import AgentProfile
from app.repositories.base import BaseRepository


class AgentRepository(BaseRepository[AgentProfile]):
    """Repository for agent profile operations."""
    
    def __init__(self, db: Session):
        super().__init__(AgentProfile, db)
    
    def get_by_user_id(self, user_id: UUID) -> Optional[AgentProfile]:
        """
        Get agent profile by user account ID.
        
        Args:
            user_id: User account UUID
            
        Returns:
            AgentProfile or None if not found
        """
        return self.db.query(AgentProfile).filter(
            AgentProfile.user_account_id == user_id
        ).first()
    
    def get_by_user_id_with_account(self, user_id: UUID) -> Optional[AgentProfile]:
        """
        Get agent profile with user account eagerly loaded.
        
        Args:
            user_id: User account UUID
            
        Returns:
            AgentProfile with account or None
        """
        return self.db.query(AgentProfile).filter(
            AgentProfile.user_account_id == user_id
        ).options(
            joinedload(AgentProfile.user_account)
        ).first()
    
    def get_with_applications(self, agent_id: UUID) -> Optional[AgentProfile]:
        """
        Get agent with all applications eagerly loaded.
        
        Args:
            agent_id: Agent profile UUID
            
        Returns:
            AgentProfile with applications or None
        """
        return self.db.query(AgentProfile).filter(
            AgentProfile.id == agent_id
        ).options(
            joinedload(AgentProfile.applications)
        ).first()
    
    def search_by_agency(
        self, 
        search_term: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[AgentProfile]:
        """
        Search agents by agency name.
        
        Args:
            search_term: Search string
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of matching agents
        """
        search_pattern = f"%{search_term}%"
        return self.db.query(AgentProfile).filter(
            AgentProfile.agency_name.ilike(search_pattern)
        ).offset(skip).limit(limit).all()
    
    def get_by_commission_rate_range(
        self,
        min_rate: float,
        max_rate: float,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentProfile]:
        """
        Get agents within commission rate range.
        
        Args:
            min_rate: Minimum commission rate
            max_rate: Maximum commission rate
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of agents
        """
        return self.db.query(AgentProfile).filter(
            AgentProfile.commission_rate >= min_rate,
            AgentProfile.commission_rate <= max_rate
        ).offset(skip).limit(limit).all()
