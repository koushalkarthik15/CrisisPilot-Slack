from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from features.missions.domain import ExecutionStrategy, MissionPriority, MissionStatus


class MissionBase(BaseModel):
    name: str = Field(..., description="Name of the mission")
    description: Optional[str] = Field(None, description="Detailed description of the mission")
    objective: str = Field(..., description="The objective of the mission")
    strategy: ExecutionStrategy = Field(default=ExecutionStrategy.MANUAL, description="How the mission will be executed")
    priority: MissionPriority = Field(default=MissionPriority.MEDIUM, description="Priority level of the mission")

class MissionCreate(MissionBase):
    operation_id: Optional[str] = None
    incident_id: Optional[str] = None
    assigned_human_ids: Optional[List[str]] = None
    assigned_mini_agent_id: Optional[str] = None

class MissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    strategy: Optional[ExecutionStrategy] = None
    priority: Optional[MissionPriority] = None

class MissionAssignment(BaseModel):
    assigned_human_ids: Optional[List[str]] = None
    assigned_mini_agent_id: Optional[str] = None

class MissionRead(MissionBase):
    id: str
    status: MissionStatus
    operation_id: Optional[str]
    incident_id: Optional[str]
    assigned_human_ids: Optional[List[str]] = None
    assigned_mini_agent_id: Optional[str] = None
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
