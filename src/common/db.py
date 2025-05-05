from sqlalchemy import create_engine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=True)

#Database Injection

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()