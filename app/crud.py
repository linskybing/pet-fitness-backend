from sqlalchemy.orm import Session
from . import models, schemas
import random

# Password hashing is omitted for simplicity.
# In a real app, use passlib:
# from passlib.context import CryptContext
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# def get_password_hash(password):
#     return pwd_context.hash(password)

# ==================
# User
# ==================

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    # hashed_password = get_password_hash(user.password) # Should use hash
    hashed_password = user.password + "_hashed" # Simple version for demo
    
    db_user = models.User(
        username=user.username, 
        email=user.email, 
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # When creating a user, automatically assign them a pet (egg)
    create_pet_for_user(db, db_user)
    
    db.refresh(db_user) # Refresh to include the new pet
    return db_user

# ==================
# Pet
# ==================

def get_pet_by_user_id(db: Session, user_id: int):
    return db.query(models.Pet).filter(models.Pet.owner_id == user_id).first()

def create_pet_for_user(db: Session, user: models.User):
    # Create a new pet, default to "EGG" stage
    db_pet = models.Pet(
        owner_id=user.id,
        name=f"{user.username}'s Pet", # Changed to English, though name is data
        stage=models.PetStage.EGG
    )
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet

# Map of levels to stages
LEVEL_STAGE_MAP = {
    1: models.PetStage.EGG,
    5: models.PetStage.CHICK,
    10: models.PetStage.CHICKEN,
    15: models.PetStage.BIG_CHICKEN,
    20: models.PetStage.BUFF_CHICKEN
}
MAX_LEVEL = 20

def get_stage_for_level(level: int) -> models.PetStage:
    stage = models.PetStage.EGG
    for lvl_threshold, stg in LEVEL_STAGE_MAP.items():
        if level >= lvl_threshold:
            stage = stg
    return stage

def update_pet_stats(db: Session, pet: models.Pet, 
                     growth: int = 0, strength: int = 0, 
                     stamina: int = 0, satiety: int = 0, mood: int = 0):
    
    pet.growth_points += growth
    pet.strength += strength
    pet.stamina = max(0, min(100, pet.stamina + stamina)) # Stamina 0-100
    pet.satiety = max(0, min(100, pet.satiety + satiety)) # Satiety 0-100
    pet.mood = max(0, min(100, pet.mood + mood)) # Mood 0-100

    # Check for level up (Example: 1 level per 100 growth points)
    new_level = (pet.growth_points // 100) + 1
    if new_level > pet.level and pet.level < MAX_LEVEL:
        pet.level = new_level
        # Give bonus on level up
        pet.stamina = 100
        pet.mood += 10
    
    # Update growth stage
    pet.stage = get_stage_for_level(pet.level)

    db.commit()
    db.refresh(pet)
    return pet

# ==================
# Exercise
# ==================

def log_exercise(db: Session, user_id: int, log: schemas.ExerciseLogCreate):
    pet = get_pet_by_user_id(db, user_id)
    if not pet:
        return None

    db_log = models.ExerciseLog(
        **log.dict(),
        user_id=user_id,
        pet_id=pet.id
    )
    db.add(db_log)
    
    # Calculate pet stat changes based on exercise
    # Example logic:
    # 1 point of volume = +2 growth, +0.1 strength
    # Cost: 10 stamina, 5 satiety
    growth_gain = int(log.volume * 2)
    strength_gain = int(log.volume * 0.1)
    stamina_cost = -10
    satiety_cost = -5

    updated_pet = update_pet_stats(
        db=db,
        pet=pet,
        growth=growth_gain,
        strength=strength_gain,
        stamina=stamina_cost,
        satiety=satiety_cost,
        mood=5 # Exercise improves mood
    )
    
    return updated_pet

# ==================
# Quest
# ==================

# Simple daily quest system
QUEST_TEMPLATES = [
    {"title": "Daily Check-in", "description": "Log in to the app", "reward_growth": 10, "reward_mood": 5},
    {"title": "Complete 1 Exercise", "description": "Complete one exercise of any type", "reward_growth": 20, "reward_stamina": 10},
    {"title": "Full of Energy", "description": "Accumulate 100 exercise volume", "reward_growth": 50, "reward_strength": 1},
]

def get_or_create_daily_quests(db: Session, user_id: int):
    # Check if quests for today have been generated (simplified logic)
    today_quests = db.query(models.UserQuest).filter(
        models.UserQuest.user_id == user_id,
        # Should add date filtering: (func.date(models.UserQuest.date) == datetime.date.today())
    ).all()
    
    if today_quests:
        return today_quests

    # First time or new day, generate new quests
    new_user_quests = []
    for quest_template in QUEST_TEMPLATES:
        # Ensure the quest exists in the Quest table
        q = db.query(models.Quest).filter(models.Quest.title == quest_template["title"]).first()
        if not q:
            q = models.Quest(**quest_template)
            db.add(q)
            db.commit()
            db.refresh(q)
        
        # Create user quest entry
        uq = models.UserQuest(quest_id=q.id, user_id=user_id)
        db.add(uq)
        new_user_quests.append(uq)
        
    db.commit()
    for uq in new_user_quests:
        db.refresh(uq) # Load the 'quest' relationship
        
    return new_user_quests

def complete_quest(db: Session, user_id: int, user_quest_id: int):
    uq = db.query(models.UserQuest).filter(
        models.UserQuest.id == user_quest_id,
        models.UserQuest.user_id == user_id
    ).first()

    if not uq or uq.is_completed:
        return None # Quest doesn't exist or is already completed
    
    uq.is_completed = True
    
    # Apply rewards
    pet = get_pet_by_user_id(db, user_id)
    updated_pet = update_pet_stats(
        db=db,
        pet=pet,
        growth=uq.quest.reward_growth,
        strength=uq.quest.reward_strength,
        stamina=uq.quest.reward_stamina,
        satiety=uq.quest.reward_satiety,
        mood=uq.quest.reward_mood
    )
    
    db.commit()
    return updated_pet

# ==================
# Travel & Leaderboard
# ==================

TAIPEI_ATTRACTIONS = [
    {"name": "Taipei 101", "description": "Once the world's tallest building"},
    {"name": "National Palace Museum", "description": "Home to a vast collection of Chinese artifacts"},
    {"name": "Longshan Temple", "description": "A popular and historic temple"},
    {"name": "Yangmingshan National Park", "description": "The 'backyard' of Taipei City"},
]

# Ensure attractions exist in the DB
def seed_attractions(db: Session):
    if db.query(models.Attraction).count() == 0:
        for att in TAIPEI_ATTRACTIONS:
            db_att = models.Attraction(
                name=att["name"], 
                description=att["description"]
            )
            db.add(db_att)
        db.commit()

def get_random_attraction(db: Session):
    seed_attractions(db) # Ensure data exists
    attractions = db.query(models.Attraction).all()
    return random.choice(attractions) if attractions else None

def get_leaderboard_by_level(db: Session, limit: int = 10):
    return db.query(models.Pet, models.User.username)\
             .join(models.User, models.Pet.owner_id == models.User.id)\
             .order_by(models.Pet.level.desc(), models.Pet.growth_points.desc())\
             .limit(limit)\
             .all()