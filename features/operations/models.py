import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from infrastructure.database import Base
from features.operations.domain import OperationStatus, OperationCategory, OperationPriority

def utc_now():
    return datetime.now(timezone.utc)

class Operation(Base):
    __tablename__ = "operations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    category = Column(SQLEnum(OperationCategory), nullable=False, default=OperationCategory.GENERIC)
    status = Column(SQLEnum(OperationStatus), nullable=False, default=OperationStatus.PLANNED)
    priority = Column(SQLEnum(OperationPriority), nullable=False, default=OperationPriority.MEDIUM)
    created_by = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
