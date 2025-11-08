import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load database URL from environment variables
# Example: "postgresql://your_user:your_password@localhost:5432/pet_fitness_db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL is None:
    print("Warning: DATABASE_URL environment variable not found. Using local SQLite as fallback.")
    # If not set, use a local sqlite file as a fallback for easy testing
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # For Docker Compose, this might be:
    # "postgresql://your_user:your_password@db:5432/pet_fitness_db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a database Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models.py to inherit from
Base = declarative_base()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()