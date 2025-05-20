import uuid
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    ForeignKey,
    String,
    DateTime,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from src.common.db import Base, engine

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True,
                index=True, default=uuid.uuid4)
    email = Column(String(255), unique=True,
                   index=True, nullable=False)
    name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    level = Column(Integer(), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    is_admin = Column(Boolean(), default=False)
    # has_completed_fees = Column(Boolean(), default=False)
    created_at = Column(DateTime(timezone=True),
                        default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), nullable=True)
    phone_number = Column(String(11), nullable=True)

Base.metadata.create_all(bind=engine)