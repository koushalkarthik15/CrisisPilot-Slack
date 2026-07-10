from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from features.operations.domain import OperationStatus, OperationCategory, OperationPriority

class OperationBase(BaseModel):
    name: str = Field(..., description="Name of the operation")
    description: Optional[str] = Field(None, description="Detailed description of the operation objective")
    category: OperationCategory = Field(default=OperationCategory.GENERIC, description="Category of the operation")
    priority: OperationPriority = Field(default=OperationPriority.MEDIUM, description="Priority level of the operation")

class OperationCreate(OperationBase):
    pass

class OperationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[OperationCategory] = None
    priority: Optional[OperationPriority] = None

class OperationRead(OperationBase):
    id: str
    status: OperationStatus
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
