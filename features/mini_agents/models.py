import uuid
from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import String, Boolean, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database import Base


class MiniAgentModel(Base):
    """
    SQLAlchemy model for persisting Mini-Agent definitions in the database.
    """
    __tablename__ = "mini_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Store allowed tools as JSON
    allowed_tools: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Provider configuration
    llm_provider: Mapped[str] = mapped_column(String(50), default="groq", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="llama-3.3-70b-versatile", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
