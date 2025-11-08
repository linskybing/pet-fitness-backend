from sqlalchemy.orm import Session
from . import models, schemas
import random
from datetime import datetime, date, time, timedelta

# Password hashing is omitted for simplicity.
# In a real app, use passlib:
# from passlib.context import CryptContext
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# def get_password_hash(password):
#     return pwd_context.hash(password)

# ==================
# User
# ==================

def get_user(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    try:
        # Check if user already exists
        existing_user = get_user(db, user.user_id)
        if existing_user:
            # User already exists, just return it
            return existing_user
        
        # Create user with provided user_id
        db_user = models.User(id=user.user_id)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # When creating a user, automatically assign them a pet with the provided name
        create_pet_for_user(db, db_user, pet_name=user.pet_name)
        
        db.refresh(db_user) # Refresh to include the new pet
        return db_user
    except Exception as e:
        db.rollback()
        print(f"Error in create_user: {e}")
        raise e

# ==================
# Pet
# ==================

def get_pet_by_user_id(db: Session, user_id: str):
    return db.query(models.Pet).filter(models.Pet.owner_id == user_id).first()

def create_pet_for_user(db: Session, user: models.User, pet_name: str):
    try:
        # Create a new pet with provided name, default to "EGG" stage
        db_pet = models.Pet(
            owner_id=user.id,
            name=pet_name,
            stage=models.PetStage.EGG,
            stamina=900  # Start with full stamina
        )
        db.add(db_pet)
        db.commit()
        db.refresh(db_pet)
        return db_pet
    except Exception as e:
        db.rollback()
        print(f"Error in create_pet_for_user: {e}")
        raise e

# Map of levels to stages (only after breakthrough)
# Stage evolution happens AFTER breakthrough at level milestones
LEVEL_STAGE_MAP = {
    1: models.PetStage.EGG,        # Level 1-4 (before lv5 breakthrough)
    5: models.PetStage.CHICK,      # After lv5 breakthrough
    10: models.PetStage.CHICKEN,   # After lv10 breakthrough
    15: models.PetStage.BIG_CHICKEN, # After lv15 breakthrough
    20: models.PetStage.BUFF_CHICKEN # After lv20 breakthrough
}
# Cache sorted thresholds to avoid repeated sorting
SORTED_LEVEL_THRESHOLDS = sorted(LEVEL_STAGE_MAP.keys(), reverse=True)

MAX_LEVEL = 25
STRENGTH_PER_LEVEL = 120  # 120 points = 1200 seconds = 20 minutes
MIN_DAILY_STRENGTH = 60   # Minimum 60 points (10 minutes) per day to maintain mood
MAX_STAMINA = 900  # Maximum stamina value, reset daily

def get_stage_for_level(level: int, breakthrough_completed: bool) -> models.PetStage:
    """
    Determine the pet's stage based on level and breakthrough status.
    Stage only changes AFTER completing breakthrough at level milestones (5, 10, 15, 20).
    """
    # If at a breakthrough level (multiple of 5) but haven't completed breakthrough, stay at previous stage
    if level % 5 == 0 and level > 1 and not breakthrough_completed:
        # Stay at previous milestone's stage
        prev_milestone = level - 5
        for lvl_threshold in SORTED_LEVEL_THRESHOLDS:
            if prev_milestone >= lvl_threshold:
                return LEVEL_STAGE_MAP[lvl_threshold]
    
    # Otherwise, find the appropriate stage for current level
    stage = models.PetStage.EGG
    for lvl_threshold in SORTED_LEVEL_THRESHOLDS:
        if level >= lvl_threshold:
            stage = LEVEL_STAGE_MAP[lvl_threshold]
            break
    return stage

def update_pet(db: Session, pet: models.Pet, update_data: schemas.PetUpdate):
    """
    Generic update function that allows updating any pet attribute.
    For strength/stamina/mood updates, uses the same logic as update_pet_stats.
    """
    update_dict = update_data.dict(exclude_unset=True)
    
    # Separate stat updates (strength, stamina, mood) from other updates
    stat_updates = {}
    other_updates = {}
    
    for key, value in update_dict.items():
        if key in ["strength", "stamina", "mood"]:
            stat_updates[key] = value
        else:
            other_updates[key] = value
    
    # Apply non-stat updates directly
    for key, value in other_updates.items():
        setattr(pet, key, value)
    
    # If there are stat updates, use update_pet_stats logic
    if stat_updates:
        # Get current values
        current_strength = pet.strength
        current_stamina = pet.stamina
        current_mood = pet.mood
        
        # Calculate deltas (difference from current to new value)
        strength_delta = stat_updates.get("strength", current_strength) - current_strength
        stamina_delta = stat_updates.get("stamina", current_stamina) - current_stamina
        mood_delta = stat_updates.get("mood", current_mood) - current_mood
        
        # Use update_pet_stats to apply changes with level-up logic
        result = update_pet_stats(
            db=db,
            pet=pet,
            strength=strength_delta,
            stamina=stamina_delta,
            mood=mood_delta
        )
        return result["pet"]
    
    # If only non-stat updates, just commit
    db.commit()
    db.refresh(pet)
    return pet

def update_pet_stats(db: Session, pet: models.Pet, 
                     strength: int = 0, stamina: int = 0, mood: int = 0):
    """
    Update pet stats with new strength-based leveling system.
    - Strength gains: 10 seconds of exercise = 1 point
    - Level up: Every 120 strength points = 1 level (20 minutes)
    - Breakthrough: At levels 5, 10, 15, 20, need breakthrough to continue gaining strength
    - Mood: Increases with exercise
    - Stamina: 0-900 range (reset daily)
    """
    try:
        # Check if at a breakthrough level and breakthrough not completed
        needs_breakthrough = (pet.level % 5 == 0) and (pet.level >= 5) and not pet.breakthrough_completed
        
        if needs_breakthrough and strength > 0:
            # Cannot gain strength without breakthrough - return warning
            # Strength gains are blocked
            strength = 0
            # Still update stamina and mood
            pet.stamina = max(0, min(MAX_STAMINA, pet.stamina + stamina))
            pet.mood = max(0, min(100, pet.mood + mood))
            db.commit()
            db.refresh(pet)
            return {"pet": pet, "breakthrough_required": True}
        
        # Apply strength gains
        pet.strength += strength
        
        # Check for level up (120 strength points = 1 level)
        while pet.strength >= STRENGTH_PER_LEVEL and pet.level < MAX_LEVEL:
            pet.strength -= STRENGTH_PER_LEVEL
            pet.level += 1
            
            # Reset stamina to full on level up
            pet.stamina = MAX_STAMINA
            pet.mood += 10  # Bonus mood on level up
            
            # Check if new level requires breakthrough
            if pet.level % 5 == 0 and pet.level >= 5:
                pet.breakthrough_completed = False
                # Stop further leveling until breakthrough
                break
        
        # Cap strength at max for current level if at breakthrough
        if pet.level % 5 == 0 and pet.level >= 5 and not pet.breakthrough_completed:
            pet.strength = 0
        
        # Update other stats
        pet.stamina = max(0, min(MAX_STAMINA, pet.stamina + stamina))
        pet.mood = max(0, min(100, pet.mood + mood))
        
        # Update growth stage based on level and breakthrough status
        pet.stage = get_stage_for_level(pet.level, pet.breakthrough_completed)
        
        db.commit()
        db.refresh(pet)
        return {"pet": pet, "breakthrough_required": False}
    except Exception as e:
        db.rollback()
        print(f"Error in update_pet_stats: {e}")
        raise e

# ==================
# Exercise
# ==================

def log_exercise(db: Session, user_id: str, log: schemas.ExerciseLogCreate):
    """
    Log exercise and update pet stats.
    New logic:
    - 10 seconds of exercise = 1 strength point
    - Stamina cost: 10 per exercise session
    - Mood increase: 5 per exercise session
    - Accumulate daily exercise time and steps
    """
    try:
        pet = get_pet_by_user_id(db, user_id)
        if not pet:
            return None

        db_log = models.ExerciseLog(
            **log.dict(),
            user_id=user_id,
            pet_id=pet.id
        )
        db.add(db_log)
        
        # Accumulate daily exercise time and steps
        pet.daily_exercise_seconds += log.duration_seconds
        pet.daily_steps += log.steps
        
        # Auto-complete daily quests if conditions met
        # Quest 2: 運動十分鐘 (600 seconds) - Mark as claimable (completed=False means can claim)
        if pet.daily_exercise_seconds >= 600 and pet.daily_quest_2_completed:
            pet.daily_quest_2_completed = False  # Ready to claim
        
        # Quest 3: 走路5000步 - Mark as claimable
        if pet.daily_steps >= 5000 and pet.daily_quest_3_completed:
            pet.daily_quest_3_completed = False  # Ready to claim
        
        # Calculate pet stat changes based on exercise duration
        # 10 seconds = 1 strength point
        strength_gain = log.duration_seconds // 10
        stamina_cost = -10
        mood_gain = 5

        result = update_pet_stats(
            db=db,
            pet=pet,
            strength=strength_gain,
            stamina=stamina_cost,
            mood=mood_gain
        )
        
        return result
    except Exception as e:
        db.rollback()
        print(f"Error in log_exercise: {e}")
        raise e

# ==================
# Daily Quest System (Independent)
# ==================

# Daily quest definitions
DAILY_QUEST_DEFINITIONS = [
    {
        "id": 1,
        "title": "每日登入",
        "description": "今天第一次登入遊戲",
        "reward_strength": 10,
        "reward_stamina": 20,
        "reward_mood": 5
    },
    {
        "id": 2,
        "title": "運動十分鐘",
        "description": "累積運動時間達到10分鐘",
        "reward_strength": 30,
        "reward_stamina": 15,
        "reward_mood": 10
    },
    {
        "id": 3,
        "title": "走路5000步",
        "description": "今日累積走路5000步",
        "reward_strength": 50,
        "reward_stamina": 20,
        "reward_mood": 15
    }
]

def get_daily_quest_status(db: Session, user_id: str):
    """Get current status of all daily quests (simplified for frontend)"""
    pet = get_pet_by_user_id(db, user_id)
    if not pet:
        return None
    
    return {
        "quest_1_completed": pet.daily_quest_1_completed,
        "quest_2_completed": pet.daily_quest_2_completed,
        "quest_3_completed": pet.daily_quest_3_completed
    }

def claim_daily_quest_reward(db: Session, user_id: str, quest_id: int):
    """Claim reward for a completed daily quest (can only claim once)"""
    try:
        pet = get_pet_by_user_id(db, user_id)
        if not pet:
            return None
        
        # Check if quest is ready to claim (completed=False means claimable)
        if quest_id == 1:
            if pet.daily_quest_1_completed:
                return {"success": False, "message": "Quest not completed yet"}
            # Mark as claimed (completed=True means already claimed)
            pet.daily_quest_1_completed = True
            quest_def = DAILY_QUEST_DEFINITIONS[0]
        elif quest_id == 2:
            if pet.daily_quest_2_completed:
                return {"success": False, "message": "Quest not completed yet"}
            pet.daily_quest_2_completed = True
            quest_def = DAILY_QUEST_DEFINITIONS[1]
        elif quest_id == 3:
            if pet.daily_quest_3_completed:
                return {"success": False, "message": "Quest not completed yet"}
            pet.daily_quest_3_completed = True
            quest_def = DAILY_QUEST_DEFINITIONS[2]
        else:
            return {"success": False, "message": "Invalid quest ID"}
        
        # Apply rewards
        result = update_pet_stats(
            db=db,
            pet=pet,
            strength=quest_def["reward_strength"],
            stamina=quest_def["reward_stamina"],
            mood=quest_def["reward_mood"]
        )
        
        return {
            "success": True,
            "message": f"Claimed reward for {quest_def['title']}",
            "pet": result["pet"],
            "rewards": {
                "strength": quest_def["reward_strength"],
                "stamina": quest_def["reward_stamina"],
                "mood": quest_def["reward_mood"]
            }
        }
    except Exception as e:
        db.rollback()
        print(f"Error in claim_daily_quest_reward: {e}")
        raise e

# ==================
# Quest
# ==================

# Simple daily quest system
QUEST_TEMPLATES = [
    {"title": "每日登入", "description": "今天第一次登入遊戲", "reward_mood": 5, "reward_stamina": 10, "reward_strength": 0},
    {"title": "運動十分鐘", "description": "累積運動時間達到10分鐘", "reward_strength": 20, "reward_stamina": 10, "reward_mood": 0},
    {"title": "走路5000步", "description": "今日累積走路5000步", "reward_strength": 30, "reward_mood": 10, "reward_stamina": 0},
]

def get_or_create_daily_quests(db: Session, user_id: str):
    try:
        # Check if quests for today have been generated (simplified logic)
        today_quests = db.query(models.UserQuest).filter(
            models.UserQuest.user_id == user_id,
            # Should add date filtering: (func.date(models.UserQuest.date) == datetime.date.today())
        ).all()
        
        if today_quests:
            return today_quests

        # First time or new day, generate new quests
        # Batch process: collect all quests first, then commit once
        quests_to_create = []
        for quest_template in QUEST_TEMPLATES:
            # Ensure the quest exists in the Quest table
            q = db.query(models.Quest).filter(models.Quest.title == quest_template["title"]).first()
            if not q:
                q = models.Quest(**quest_template)
                db.add(q)
                quests_to_create.append(("new", q, quest_template))
            else:
                quests_to_create.append(("existing", q, quest_template))
        
        # Commit new quests if any
        if any(status == "new" for status, _, _ in quests_to_create):
            db.commit()
            # Refresh new quests
            for status, q, _ in quests_to_create:
                if status == "new":
                    db.refresh(q)
        
        # Create all user quest entries
        new_user_quests = []
        for _, q, _ in quests_to_create:
            uq = models.UserQuest(quest_id=q.id, user_id=user_id)
            db.add(uq)
            new_user_quests.append(uq)
        
        # Single commit for all user quests
        db.commit()
        
        # Load relationships
        for uq in new_user_quests:
            db.refresh(uq) # Load the 'quest' relationship
            
        return new_user_quests
    except Exception as e:
        db.rollback()
        print(f"Error in get_or_create_daily_quests: {e}")
        raise e

def complete_quest(db: Session, user_id: str, user_quest_id: int):
    try:
        uq = db.query(models.UserQuest).filter(
            models.UserQuest.id == user_quest_id,
            models.UserQuest.user_id == user_id
        ).first()

        if not uq or uq.is_completed:
            return None # Quest doesn't exist or is already completed
        
        # Mark quest as completed
        uq.is_completed = True
        db.commit()  # Commit the quest completion first
        
        # Apply rewards
        pet = get_pet_by_user_id(db, user_id)
        result = update_pet_stats(
            db=db,
            pet=pet,
            strength=uq.quest.reward_strength,
            stamina=uq.quest.reward_stamina,
            mood=uq.quest.reward_mood
        )
        
        # No need to commit again - update_pet_stats already commits
        return result
    except Exception as e:
        db.rollback()
        print(f"Error in complete_quest: {e}")
        raise e

# ==================
# Travel & Leaderboard
# ==================

def perform_daily_check(db: Session, user_id: str):
    """
    Perform daily check at 00:00 to verify if user exercised enough yesterday.
    - Resets stamina to 900 for the new day
    - If user didn't exercise at least 10 minutes (60 strength points), decrease mood
    - If mood reaches 0 and strength > 0, decrease strength
    """
    pet = get_pet_by_user_id(db, user_id)
    if not pet:
        return None
    
    try:
        now = datetime.now()
        today_start = datetime.combine(date.today(), time.min)
        
        # Check if daily check already performed today
        if pet.last_daily_check:
            # Need to make both timezone-aware or both naive for comparison
            pet_check_date = pet.last_daily_check
            if pet_check_date.tzinfo is None:
                pet_check_date = pet_check_date.replace(tzinfo=None)
                today_start = today_start.replace(tzinfo=None)
            
            if pet_check_date.date() >= today_start.date():
                # Already checked today, just refresh pet and return
                db.refresh(pet)
                return {
                    "pet": pet, 
                    "already_checked": True, 
                    "met_requirement": True,
                    "total_strength_yesterday": 0
                }
        
        # Get yesterday's exercise logs
        yesterday_start = today_start - timedelta(days=1)
        yesterday_exercises = db.query(models.ExerciseLog).filter(
            models.ExerciseLog.user_id == user_id,
            models.ExerciseLog.created_at >= yesterday_start,
            models.ExerciseLog.created_at < today_start
        ).all()
        
        # Calculate total strength points gained yesterday (10 seconds = 1 point)
        total_strength_yesterday = sum(log.duration_seconds // 10 for log in yesterday_exercises)
        
        # Check if met minimum requirement (60 points = 10 minutes)
        met_requirement = total_strength_yesterday >= MIN_DAILY_STRENGTH
        
        # Reset stamina to 900 for the new day
        pet.stamina = MAX_STAMINA
        
        # Reset daily exercise tracking
        pet.daily_exercise_seconds = 0
        pet.daily_steps = 0
        pet.last_reset_date = now
        
        # Reset daily quests and complete Quest 1 (daily login)
        pet.daily_quest_1_completed = False  # Quest 1: 每日登入 (ready to claim on login)
        pet.daily_quest_2_completed = True   # Quest 2: 運動十分鐘 (not yet achieved)
        pet.daily_quest_3_completed = True   # Quest 3: 走路5000步 (not yet achieved)
        
        if not met_requirement:
            # Didn't meet requirement - decrease mood
            pet.mood = max(0, pet.mood - 10)
            
            # If mood reaches 0 and strength > 0, decrease strength
            if pet.mood == 0 and pet.strength > 0:
                pet.strength = max(0, pet.strength - 10)
        
        # Update last daily check timestamp
        pet.last_daily_check = now
        
        db.commit()
        db.refresh(pet)
        
        return {
            "pet": pet, 
            "already_checked": False, 
            "met_requirement": met_requirement,
            "total_strength_yesterday": total_strength_yesterday
        }
    except Exception as e:
        db.rollback()
        # Log the error for debugging
        print(f"Error in perform_daily_check: {e}")
        raise e

def complete_breakthrough(db: Session, user_id: str):
    """
    Complete breakthrough by traveling to an attraction.
    This allows the pet to continue leveling past level 5, 10, 15, 20.
    """
    try:
        pet = get_pet_by_user_id(db, user_id)
        if not pet:
            return None
        
        # Check if at a breakthrough level
        if pet.level % 5 != 0 or pet.level < 5:
            return {"success": False, "message": "Not at a breakthrough level"}
        
        if pet.breakthrough_completed:
            return {"success": False, "message": "Breakthrough already completed for this level"}
        
        # Mark breakthrough as completed
        pet.breakthrough_completed = True
        
        # Update stage after breakthrough
        pet.stage = get_stage_for_level(pet.level, pet.breakthrough_completed)
        
        db.commit()
        db.refresh(pet)
        
        return {"success": True, "pet": pet, "message": "Breakthrough completed!"}
    except Exception as e:
        db.rollback()
        print(f"Error in complete_breakthrough: {e}")
        raise e

# ==================
# Travel & Leaderboard (continued)
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
    return db.query(models.Pet, models.User.id)\
             .join(models.User, models.Pet.owner_id == models.User.id)\
             .order_by(models.Pet.level.desc(), models.Pet.strength.desc())\
             .limit(limit)\
             .all()

# ==================
# Travel Checkins (Location-based quests)
# ==================

def get_user_travel_checkins(db: Session, user_id: str):
    "Get all travel checkins for a user"
    return db.query(models.TravelCheckin).filter(models.TravelCheckin.user_id == user_id).order_by(models.TravelCheckin.completed_at.desc()).all()

def create_travel_checkin(db: Session, user_id: str, checkin: schemas.TravelCheckinCreate):
    "Create a new travel checkin and reward the pet."
    try:
        pet = get_pet_by_user_id(db, user_id)
        if not pet:
            raise ValueError("Pet not found")
        
        # Check if already checked in at this location
        existing = db.query(models.TravelCheckin).filter(
            models.TravelCheckin.user_id == user_id,
            models.TravelCheckin.quest_id == checkin.quest_id
        ).first()
        if existing:
            raise ValueError("Already checked in at this location")
        
        # Create checkin record
        db_checkin = models.TravelCheckin(
            user_id=user_id, 
            quest_id=checkin.quest_id, 
            lat=checkin.lat, 
            lng=checkin.lng
        )
        db.add(db_checkin)
        db.commit()
        db.refresh(db_checkin)
        
        # Check if at a breakthrough level and auto-complete breakthrough
        at_breakthrough = (pet.level % 5 == 0) and (pet.level >= 5) and not pet.breakthrough_completed
        if at_breakthrough:
            pet.breakthrough_completed = True
            pet.stage = get_stage_for_level(pet.level, pet.breakthrough_completed)
            db.commit()
            db.refresh(pet)
        
        # Apply rewards using update_pet_stats for proper level-up logic
        # Give stamina reward for travel checkin
        result = update_pet_stats(
            db=db,
            pet=pet,
            strength=15,
            stamina=10,  # Add stamina reward
            mood=10
        )
        
        return {"pet": result["pet"], "checkin": db_checkin, "breakthrough_completed": at_breakthrough}
    except Exception as e:
        db.rollback()
        print(f"Error in create_travel_checkin: {e}")
        raise e
