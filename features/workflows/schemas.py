from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from features.workflows.domain import (
    WorkflowPriority,
    WorkflowStageType,
    WorkflowStatus,
)


class WorkflowBase(BaseModel):
    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(None, description="Detailed description of the workflow")
    category: Optional[str] = Field(None, description="Category of the workflow")
    priority: WorkflowPriority = Field(default=WorkflowPriority.MEDIUM, description="Priority level")
    stages: List[WorkflowStageType] = Field(..., description="Ordered list of workflow stages")

class WorkflowCreate(WorkflowBase):
    operation_id: Optional[str] = None
    incident_id: Optional[str] = None

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[WorkflowPriority] = None

class WorkflowRead(WorkflowBase):
    id: str
    status: WorkflowStatus
    current_stage_index: int
    operation_id: Optional[str]
    incident_id: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
