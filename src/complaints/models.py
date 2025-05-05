import uuid
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    Boolean,
    DateTime,
    func
)
from sqlalchemy.dialects.postgresql import(
    UUID,
    ENUM
)
from src.common.db import Base, engine
from src.common.enums import (
    Status,
    ComplainCategory
)

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(UUID(as_uuid=True), primary_key=True,
                index=True, default=uuid.uuid4)
    title = Column(String(64), nullable=False)
    content = Column(String(128), nullable=True)
    category = Column(ENUM(ComplainCategory), default=ComplainCategory.GENERAL)
    status = Column(ENUM(Status), default=Status.OPENED)
    # no_of_complaints = Column(Integer())

class ComplaintUser(Base):
    __tablename__ = "complains_logs"
    complaint_id = Column(ForeignKey("complaints.id"), primary_key=True)
    created_by = Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    resolved_by = Column(ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=True)
    resolved_at = Column(DateTime(timezone=False), nullable=True)

Base.metadata.create_all(bind=engine)