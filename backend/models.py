from sqlalchemy import Column, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.sql import func

from backend.database import Base


class LLMPatientIntelligence(Base):
    __tablename__ = "llm_patient_intelligence"
    __table_args__ = (
        UniqueConstraint("patient_id", "source_hash", name="uq_llm_patient_source_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, index=True, nullable=False)
    source_hash = Column(String, index=True, nullable=False)
    llm_provider = Column(String, default="openai", nullable=False)
    model_name = Column(String, nullable=True)
    intelligence_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
