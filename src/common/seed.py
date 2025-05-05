import uuid
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.common.db import engine
from src.auth.models import User 
from src.hostels.models import Hall, Room, RoomAllocation
from src.complaints.models import Complaint, ComplaintUser
from src.common.enums import Status, ComplainCategory, AllocationStatus
from src.common.security import hash_password

def seed_db():
    try:
        with Session(bind=engine) as session:
            # Users
            user1 = User(
                id=uuid.uuid4(),
                email="john.doe@example.com",
                name="John Doe",
                department="Engineering",
                hashed_password=hash_password("hashedpassword1"),
                level=400,
                is_admin=False
            )
            user2 = User(
                id=uuid.uuid4(),
                email="admins@example.com",
                name="Admin User",
                department="Admin",
                hashed_password=hash_password("adminpass"),
                level=None,
                is_admin=True
            )
            user3 = User(
                id=uuid.uuid4(),
                email="admin@example.com",
                name="Admin User",
                department="Admin",
                hashed_password=hash_password("admin123"),
                level=None,
                is_admin=True
            )

            session.add_all([user1, user2, user3])
            session.flush()

            # Complaint
            complaint = Complaint(
                title="Broken Window",
                content="The window in Room 202 is broken.",
                category=ComplainCategory.GENERAL,
                status=Status.OPENED
            )

            session.add(complaint)
            session.flush()

            # ComplaintUser
            complaint_user = ComplaintUser(
                complaint_id=complaint.id,
                created_by=user1.id,
                created_at=datetime.now(UTC)
            )

            session.add(complaint_user)

            # Hall
            hall = Hall(
                name="Main Hall",
                no_of_rooms=10,
                min_level=100,
                max_level=500,
                total_available_capacity=50,
                is_open_for_allocation=True,
                academic_year="2024-2025"
            )

            session.add(hall)
            session.flush()

            # Room
            room = Room(
                hall_id=hall.id,
                capacity=4,
                current_occupancy=1,
                room_number="101",
                is_available=True
            )

            session.add(room)
            session.flush()

            # RoomAllocation
            allocation = RoomAllocation(
                user_id=user1.id,
                room_id=room.id,
                hall_id=hall.id,
                status=AllocationStatus.ALLOCATED,
                academic_year="2024-2025"
            )

            session.add(allocation)

            # Commit all
            session.commit()
            print("Seed data inserted successfully.")

    except IntegrityError as e:
        session.rollback()
        print("Integrity error occurred while seeding the database:")
        print(e.orig)  # This shows the database-level error message

