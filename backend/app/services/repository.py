"""
Database persistence layer for storing and retrieving company insights.
Supports Firestore and Postgres; currently stubbed for in-memory storage.
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod

from app.models.company import CompanyInsight
from app.core.config import settings

logger = logging.getLogger(__name__)


class Repository(ABC):
    """Abstract base class for database repositories."""
    
    @abstractmethod
    async def get_company_by_canonical_name(self, canonical_name: str) -> Optional[CompanyInsight]:
        """Retrieve a company insight by canonical name."""
        pass
    
    @abstractmethod
    async def save_company_insight(self, insight: CompanyInsight) -> bool:
        """Save or update a company insight."""
        pass
    
    @abstractmethod
    async def delete_company(self, canonical_name: str) -> bool:
        """Delete a company insight."""
        pass


class InMemoryRepository(Repository):
    """
    In-memory repository implementation for development and testing.
    Replace with FirestoreRepository or PostgresRepository for production.
    """
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._storage: dict[str, CompanyInsight] = {}
        logger.info("Using in-memory repository (not suitable for production)")
    
    async def get_company_by_canonical_name(self, canonical_name: str) -> Optional[CompanyInsight]:
        """Retrieve a company from memory."""
        return self._storage.get(canonical_name)
    
    async def save_company_insight(self, insight: CompanyInsight) -> bool:
        """Store a company in memory."""
        try:
            self._storage[insight.canonical_name] = insight
            logger.debug(f"Saved company {insight.canonical_name} to in-memory storage")
            return True
        except Exception as e:
            logger.error(f"Error saving company {insight.canonical_name}: {e}")
            return False
    
    async def delete_company(self, canonical_name: str) -> bool:
        """Delete a company from memory."""
        try:
            if canonical_name in self._storage:
                del self._storage[canonical_name]
                logger.debug(f"Deleted company {canonical_name} from in-memory storage")
            return True
        except Exception as e:
            logger.error(f"Error deleting company {canonical_name}: {e}")
            return False


class FirestoreRepository(Repository):
    """
    Firestore repository implementation.
    
    TODO: Implement Firestore integration
    - Initialize Firebase Admin SDK with credentials from settings.FIRESTORE_CREDENTIALS_PATH
    - Use settings.FIRESTORE_PROJECT_ID for project ID
    - Collection: "companies"
    - Document ID: canonical_name
    """
    
    def __init__(self):
        """Initialize Firestore client."""
        logger.warning("FirestoreRepository not yet implemented. Using in-memory storage.")
        self._fallback = InMemoryRepository()
    
    async def get_company_by_canonical_name(self, canonical_name: str) -> Optional[CompanyInsight]:
        """Retrieve from Firestore."""
        # TODO: Implement Firestore retrieval
        return await self._fallback.get_company_by_canonical_name(canonical_name)
    
    async def save_company_insight(self, insight: CompanyInsight) -> bool:
        """Save to Firestore."""
        # TODO: Implement Firestore save
        return await self._fallback.save_company_insight(insight)
    
    async def delete_company(self, canonical_name: str) -> bool:
        """Delete from Firestore."""
        # TODO: Implement Firestore delete
        return await self._fallback.delete_company(canonical_name)


class PostgresRepository(Repository):
    """
    PostgreSQL repository implementation.
    
    TODO: Implement PostgreSQL integration
    - Use SQLAlchemy ORM with async support
    - Connection string from settings.DATABASE_URL
    - Table: companies with columns:
      - canonical_name (PRIMARY KEY)
      - name
      - website
      - authenticityScore
      - scamRisk
      - companyType
      - flags (JSON)
      - sources (JSON)
      - lastCheckedAt (timestamp)
    """
    
    def __init__(self):
        """Initialize database client."""
        logger.warning("PostgresRepository not yet implemented. Using in-memory storage.")
        self._fallback = InMemoryRepository()
    
    async def get_company_by_canonical_name(self, canonical_name: str) -> Optional[CompanyInsight]:
        """Retrieve from PostgreSQL."""
        # TODO: Implement PostgreSQL retrieval
        return await self._fallback.get_company_by_canonical_name(canonical_name)
    
    async def save_company_insight(self, insight: CompanyInsight) -> bool:
        """Save to PostgreSQL."""
        # TODO: Implement PostgreSQL save
        return await self._fallback.save_company_insight(insight)
    
    async def delete_company(self, canonical_name: str) -> bool:
        """Delete from PostgreSQL."""
        # TODO: Implement PostgreSQL delete
        return await self._fallback.delete_company(canonical_name)


def get_repository() -> Repository:
    """
    Factory function to get the appropriate repository based on settings.
    """
    if settings.FIRESTORE_PROJECT_ID:
        logger.info("Initializing Firestore repository")
        return FirestoreRepository()
    elif settings.DATABASE_URL:
        logger.info("Initializing PostgreSQL repository")
        return PostgresRepository()
    else:
        logger.info("No database configured, using in-memory repository")
        return InMemoryRepository()


# Global repository instance
_repository: Optional[Repository] = None


def get_db_service() -> Repository:
    """Get or initialize the global repository service."""
    global _repository
    if _repository is None:
        _repository = get_repository()
    return _repository
