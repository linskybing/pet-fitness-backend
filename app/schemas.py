from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .models import PetStage

# ==================
# Base models (for create/update)
# ==================

class PetBase(BaseModel):
    name: Optional[str] = "我的手雞"
    strength: int = 0
    stamina: int = 100
    mood: int = 0
    level: int = 1
    stage: PetStage = PetStage.EGG
    breakthrough_completed: bool = False
    daily_exercise_seconds: int = 0

class PetCreate(PetBase):
    pass

class PetUpdate(BaseModel):
    name: Optional[str] = None
    strength: Optional[int] = None
    stamina: Optional[int] = None
    mood: Optional[int] = None
    level: Optional[int] = None
    stage: Optional[PetStage] = None
    breakthrough_completed: Optional[bool] = None
    daily_exercise_seconds: Optional[int] = None

class UserBase(BaseModel):
    pass

class UserCreate(BaseModel):
    user_id: str  # TownPass ID
    pet_name: str  # Pet name is required

class ExerciseLogBase(BaseModel):
    exercise_type: str
    duration_seconds: int
    volume: float

class ExerciseLogCreate(ExerciseLogBase):
    pass

class QuestBase(BaseModel):
    title: str
    description: Optional[str] = None
    reward_strength: int = 0
    reward_stamina: int = 0
    reward_mood: int = 0

class AttractionBase(BaseModel):
    name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class TravelCheckinBase(BaseModel):
    quest_id: str
    lat: float
    lng: float

class TravelCheckinCreate(TravelCheckinBase):
    pass


# ==================
# Response models (reading from DB)
# ==================

class Pet(PetBase):
    id: int
    owner_id: str  # String to match User.id (TownPass ID)
    updated_at: Optional[datetime]
    last_daily_check: Optional[datetime] = None
    last_reset_date: Optional[datetime] = None

    class Config:
        from_attributes = True # Pydantic v2 (formerly orm_mode=True)

class ExerciseLog(ExerciseLogBase):
    id: int
    created_at: datetime
    user_id: str  # String to match User.id
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
    user_id: str  # String to match User.id
    date: datetime
    is_completed: bool
    quest: Quest # Nested display for quest details

    class Config:
        from_attributes = True

class User(UserBase):
    id: str  # TownPass ID (string)
    created_at: datetime
    pet: Optional[Pet] = None # Nested display for pet
    exercise_logs: List[ExerciseLog] = [] # Nested display for exercise logs
    
    class Config:
        from_attributes = True

class Attraction(AttractionBase):
    id: int
    
    class Config:
        from_attributes = True

class TravelCheckin(TravelCheckinBase):
    id: int
    user_id: str  # String to match User.id
    completed_at: datetime
    
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