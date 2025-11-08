from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from . import crud, models, schemas
from .database import SessionLocal, engine, get_db

# Create all database tables
# In production, you might use Alembic for database migrations
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pet Fitness API",
    description="Backend API for a fitness and virtual pet app",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tamagotchi-city.vercel.app",
        "http://localhost:8080"  # 開發環境
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================
# Application startup event (for seeding data)
# ==================
@app.on_event("startup")
def on_startup():
    # On app start, seed some basic data
    db = SessionLocal()
    try:
        # Seed attractions
        crud.seed_attractions(db)
        # Seed daily quest templates
        for quest_template in crud.QUEST_TEMPLATES:
            q = db.query(models.Quest).filter(models.Quest.title == quest_template["title"]).first()
            if not q:
                q = models.Quest(**quest_template)
                db.add(q)
        db.commit()
    finally:
        db.close()


# ==================
# User & Auth (Simple)
# ==================
@app.post("/users/", response_model=schemas.User, tags=["User"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.
    
    - pet_name: Required, name for the pet
    - Returns user with id (use this id for all subsequent API calls)
    - An "Egg" stage pet with the provided name is automatically created
    """
    return crud.create_user(db=db, user=user)

@app.get("/users/{user_id}", response_model=schemas.User, tags=["User"])
def read_user(user_id: str, db: Session = Depends(get_db)):
    """
    Get user information by ID (includes pet status).
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# ==================
# Pet (The Chicken)
# ==================
@app.get("/users/{user_id}/pet", response_model=schemas.Pet, tags=["Pet"])
def get_user_pet(user_id: str, db: Session = Depends(get_db)):
    """
    Get the current status of the specified user's pet.
    Automatically resets daily stats if it's a new day.
    """
    pet = crud.get_pet_by_user_id(db, user_id=user_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found for this user")
    
    # Reset daily stats if needed (new day)
    crud.reset_daily_stats_if_needed(db, pet)
    db.refresh(pet)
    
    return pet

@app.patch("/users/{user_id}/pet", response_model=schemas.Pet, tags=["Pet"])
def update_user_pet(user_id: str, pet_update: schemas.PetUpdate, db: Session = Depends(get_db)):
    """
    Update any attributes of the user's pet.
    
    You can update any combination of:
    - name: Pet name
    - strength: Strength value (0-120)
    - stamina: Stamina value (0-100)
    - mood: Mood value (0-100)
    - level: Pet level
    - stage: Growth stage (0-4)
    - breakthrough_completed: Whether breakthrough is completed
    
    Only the fields you provide will be updated.
    """
    pet = crud.get_pet_by_user_id(db, user_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    
    return crud.update_pet(db, pet, pet_update)

# ==================
# Exercise
# ==================
@app.post("/users/{user_id}/exercise", tags=["Exercise"])
def log_exercise(user_id: str, log: schemas.ExerciseLogCreate, db: Session = Depends(get_db)):
    """
    Log an exercise session.
    
    Pass in the exercise type, duration, and volume (scalar).
    The server will automatically calculate strength gains (10 seconds = 1 point),
    stamina cost, mood increase, and check for level ups.
    
    Returns the updated pet status and a flag indicating if breakthrough is required.
    """
    result = crud.log_exercise(db, user_id, log)
    if result is None:
        raise HTTPException(status_code=404, detail="User or pet not found")
    return result

# ==================
# Daily Quests
# ==================
@app.get("/users/{user_id}/quests", response_model=List[schemas.UserQuest], tags=["Quests"])
def get_daily_quests(user_id: str, db: Session = Depends(get_db)):
    """
    Get the user's daily quest list.
    
    If quests for the day have not been generated, this will create them.
    """
    quests = crud.get_or_create_daily_quests(db, user_id)
    return quests

@app.post("/users/{user_id}/quests/{user_quest_id}/complete", tags=["Quests"])
def complete_daily_quest(user_id: str, user_quest_id: int, db: Session = Depends(get_db)):
    """
    Report a specific quest as complete.
    
    The server marks the quest as complete and applies the rewards
    (updating the pet's status).
    
    Returns success status and updated pet information.
    Will return error if quest is already completed (preventing duplicate rewards).
    """
    result = crud.complete_quest(db, user_id, user_quest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Cannot complete quest"))
    
    return result

# ==================
# Daily Check
# ==================
@app.post("/users/{user_id}/daily-check", tags=["Pet"])
def perform_daily_check(user_id: str, db: Session = Depends(get_db)):
    """
    Perform daily check to verify if user exercised enough yesterday.
    
    Should be called at 00:00 or when user logs in each day.
    - Checks if user exercised at least 10 minutes (60 strength points) yesterday
    - If not and stamina > 0, decreases mood
    - If mood reaches 0 and strength > 0, decreases strength
    - If stamina is 0, doesn't decrease mood (already exercised enough)
    """
    result = crud.perform_daily_check(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User or pet not found")
    return result

# ==================
# Travel (Breakthrough)
# ==================
@app.get("/travel/attractions", response_model=List[schemas.Attraction], tags=["Travel"])
def get_all_attractions(db: Session = Depends(get_db)):
    """
    Get all available travel attractions (Placeholders).
    """
    return db.query(models.Attraction).all()

@app.get("/users/{user_id}/travel/checkins", response_model=List[schemas.TravelCheckin], tags=["Travel"])
def get_user_travel_checkins(user_id: str, db: Session = Depends(get_db)):
    """
    Get all travel checkins (completed location-based quests) for a user.
    
    Returns a list of all locations where the user has checked in.
    """
    return crud.get_user_travel_checkins(db, user_id)

@app.post("/users/{user_id}/travel/checkins", tags=["Travel"])
def create_travel_checkin(
    user_id: str, 
    checkin: schemas.TravelCheckinCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new travel checkin at a location-based quest.
    
    When a user visits a quest location and checks in, this endpoint:
    - Records the checkin with quest_id, lat, lng, and timestamp
    - Rewards the pet with strength and mood bonuses
    - Prevents duplicate checkins at the same location
    
    Returns the updated pet and checkin record.
    """
    try:
        result = crud.create_travel_checkin(db, user_id, checkin)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/{user_id}/travel/breakthrough", tags=["Travel"])
def complete_breakthrough(user_id: str, db: Session = Depends(get_db)):
    """
    Complete a breakthrough to continue leveling past levels 5, 10, 15, 20.
    
    When a pet reaches a multiple of level 5, they need to complete a breakthrough
    (by traveling to an attraction) to continue gaining strength points and leveling up.
    
    Returns success status and updated pet information.
    """
    result = crud.complete_breakthrough(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return result

@app.post("/users/{user_id}/travel/start", response_model=schemas.Attraction, tags=["Travel"])
def start_travel_quest(user_id: str, db: Session = Depends(get_db)):
    """
    Get a random attraction for breakthrough quest.
    
    Returns a random Taipei attraction that can be used for breakthrough.
    """
    pet = crud.get_pet_by_user_id(db, user_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    # Check if at a breakthrough level
    if pet.level % 5 != 0 or pet.level < 5:
        raise HTTPException(
            status_code=400, 
            detail="Pet is not at a breakthrough level (5, 10, 15, 20)."
        )
    
    if pet.breakthrough_completed:
        raise HTTPException(
            status_code=400,
            detail="Breakthrough already completed for this level."
        )

    attraction = crud.get_random_attraction(db)
    if not attraction:
        raise HTTPException(status_code=500, detail="No travel attractions available")
        
    return attraction

# ==================
# Leaderboard
# ==================
@app.get("/leaderboard/level", response_model=List[schemas.LeaderboardEntry], tags=["Leaderboard"])
def get_level_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    """
    Get the pet level leaderboard.
    """
    leaderboard_data = crud.get_leaderboard_by_level(db, limit=limit)
    
    # Convert to LeaderboardEntry schema
    return [
        schemas.LeaderboardEntry(username=pet.name, value=pet.level)
        for pet, user_id in leaderboard_data
    ]