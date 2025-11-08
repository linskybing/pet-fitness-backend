from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .models import PetStage

# ==================
# Base models (for create/update)
# ==================

class PetBase(BaseModel):
    name: Optional[str] = "我的手雞"
    strength: int = 5
    stamina: int = 20
    satiety: int = 50
    mood: int = 50
    growth_points: int = 0
    level: int = 1
    stage: PetStage = PetStage.EGG

class PetCreate(PetBase):
    pass

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str # Password required on input

class ExerciseLogBase(BaseModel):
    exercise_type: str
    duration_seconds: int
    volume: float

class ExerciseLogCreate(ExerciseLogBase):
    pass

class QuestBase(BaseModel):
    title: str
    description: Optional[str] = None
    reward_growth: int = 0
    reward_strength: int = 0
    reward_satiety: int = 0
    reward_mood: int = 0

class AttractionBase(BaseModel):
    name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ==================
# Response models (reading from DB)
# ==================

class Pet(PetBase):
    id: int
    owner_id: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True # Pydantic v2 (formerly orm_mode=True)

class ExerciseLog(ExerciseLogBase):
    id: int
    created_at: datetime
    user_id: int
    pet_id: int
    
    class Config:
        from_attributes = True

class Quest(QuestBase):
    id: int
    
    class Config:
        from_attributes = True

class UserQuest(BaseModel):
    id: int
    quest_id: int
    user_id: int
    date: datetime
    is_completed: bool
    quest: Quest # Nested display for quest details

    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    created_at: datetime
    pet: Optional[Pet] = None # Nested display for pet
    exercise_logs: List[ExerciseLog] = [] # Nested display for exercise logs
    
    class Config:
        from_attributes = True

class Attraction(AttractionBase):
    id: int
    
    class Config:
        from_attributes = True

# For leaderboards
class LeaderboardEntry(BaseModel):
    username: str
    value: int # Can be level, exercise volume, etc.

# For JWT Authentication (optional but recommended)
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None