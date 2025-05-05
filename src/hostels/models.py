import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Boolean,
    DateTime,
    Enum,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.common.enums import AllocationStatus
from src.common.db import Base, engine

# Add to your existing models.py file



# Using the existing User model instead of creating a separate Student model
class RoomAllocation(Base):
    __tablename__ = "room_allocations"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    room_id = Column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    hall_id = Column(ForeignKey("halls.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(AllocationStatus), nullable=False, default=AllocationStatus.PENDING)
    allocated_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    vacated_at = Column(DateTime(timezone=True), nullable=True)
    academic_year = Column(String(20), nullable=False)  # e.g., "2024-2025"
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    user = relationship("User", backref="allocation")
    room = relationship("Room", backref="allocations")
    hall = relationship("Hall")

# Update the Room model to add current_occupancy
class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer(), primary_key=True)
    hall_id = Column(ForeignKey("halls.id", ondelete="CASCADE"), nullable=False)
    capacity = Column(Integer(), nullable=False)
    current_occupancy = Column(Integer(), default=0)
    room_number = Column(String(20), nullable=False)
    is_available = Column(Boolean(), default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    hall = relationship("Hall", back_populates="rooms")

# Update Hall model with additional tracking fields
class Hall(Base):
    __tablename__ = "halls"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    no_of_rooms = Column(Integer(), nullable=False)
    min_level = Column(Integer(), nullable=False)
    max_level = Column(Integer(), nullable=False)
    total_available_capacity = Column(Integer())
    is_open_for_allocation = Column(Boolean(), default=False)
    academic_year = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    rooms = relationship("Room", back_populates="hall", cascade="all, delete")

# Create or update tables
Base.metadata.create_all(bind=engine)