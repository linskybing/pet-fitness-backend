from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .database import Base

# Define pet growth stages
class PetStage(int, enum.Enum):
    EGG = 0
    CHICK = 1
    CHICKEN = 2
    BIG_CHICKEN = 3
    BUFF_CHICKEN = 4

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # TownPass ID (string)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Create relationship with Pet
    pet = relationship("Pet", back_populates="owner", uselist=False, cascade="all, delete-orphan")
    # Create relationship with ExerciseLog
    exercise_logs = relationship("ExerciseLog", back_populates="user", cascade="all, delete-orphan")
    # Create relationship with UserQuest
    quests = relationship("UserQuest", back_populates="user", cascade="all, delete-orphan")
    # Create relationship with TravelCheckin
    travel_checkins = relationship("TravelCheckin", back_populates="user", cascade="all, delete-orphan")

class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="我的手雞")
    
    # Stats
    strength = Column(Integer, default=0) # Strength (0-120, resets after level up)
    stamina = Column(Integer, default=100) # Stamina (consumed and restored, 0-100)
    mood = Column(Integer, default=0) # Mood (starts at 0, increases with exercise)
    level = Column(Integer, default=1) # Level
    
    # Daily tracking
    daily_exercise_seconds = Column(Integer, default=0) # Today's accumulated exercise time in seconds
    last_reset_date = Column(DateTime(timezone=True), nullable=True) # Last date when daily stats were reset
    
    # Breakthrough tracking
    breakthrough_completed = Column(Boolean, default=False) # Tracks if breakthrough is needed
    last_daily_check = Column(DateTime(timezone=True), nullable=True) # Last time daily check was performed
    
    # Growth Stage
    stage = Column(SAEnum(PetStage), default=PetStage.EGG)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Create relationship with User
    owner_id = Column(String, ForeignKey("users.id"))  # String to match User.id
    owner = relationship("User", back_populates="pet")
    
    # Create relationship with ExerciseLog
    exercise_logs = relationship("ExerciseLog", back_populates="pet")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_type = Column(String, index=True) # "Stationary", "Running"
    duration_seconds = Column(Integer)
    volume = Column(Float) # Exercise volume (scalar)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_id = Column(String, ForeignKey("users.id"))  # String to match User.id
    pet_id = Column(Integer, ForeignKey("pets.id"))

    user = relationship("User", back_populates="exercise_logs")
    pet = relationship("Pet", back_populates="exercise_logs")

# Static definitions for daily quests
class Quest(Base):
    __tablename__ = "quests"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True)
    description = Column(String)
    # Rewards
    reward_strength = Column(Integer, default=0)
    reward_stamina = Column(Integer, default=0)
    reward_mood = Column(Integer, default=0)

# User's quest status
class UserQuest(Base):
    __tablename__ = "user_quests"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("quests.id"))
    user_id = Column(String, ForeignKey("users.id"))  # String to match User.id
    date = Column(DateTime(timezone=True), server_default=func.now())
    is_completed = Column(Boolean, default=False)

    user = relationship("User", back_populates="quests")
    quest = relationship("Quest")

# Travel checkins (location-based quests)
class TravelCheckin(Base):
    __tablename__ = "travel_checkins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))  # String to match User.id
    quest_id = Column(String, index=True)  # ID from frontend JSON (e.g., "taipei-101")
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    lat = Column(Float)  # Latitude where checkin occurred
    lng = Column(Float)  # Longitude where checkin occurred
    
    user = relationship("User", back_populates="travel_checkins")

# Attractions (for breakthrough quests)
class Attraction(Base):
    __tablename__ = "attractions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)