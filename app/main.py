from fastapi import FastAPI, Depends, HTTPException, status
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
    
    - After creating the user, an "Egg" stage pet is automatically assigned.
    """
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/{user_id}", response_model=schemas.User, tags=["User"])
def read_user(user_id: int, db: Session = Depends(get_db)):
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
def get_user_pet(user_id: int, db: Session = Depends(get_db)):
    """
    Get the current status of the specified user's pet.
    """
    pet = crud.get_pet_by_user_id(db, user_id=user_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found for this user")
    return pet

@app.post("/users/{user_id}/pet/feed", response_model=schemas.Pet, tags=["Pet"])
def feed_pet(user_id: int, db: Session = Depends(get_db)):
    """
    Feed the pet.
    - Effect: Satiety +20, Mood +5
    """
    pet = crud.get_pet_by_user_id(db, user_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    
    return crud.update_pet_stats(db, pet, satiety=20, mood=5)

@app.post("/users/{user_id}/pet/play", response_model=schemas.Pet, tags=["Pet"])
def play_with_pet(user_id: int, db: Session = Depends(get_db)):
    """
    Play with the pet.
    - Effect: Mood +15, Satiety -5, Stamina -5
    """
    pet = crud.get_pet_by_user_id(db, user_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
        
    return crud.update_pet_stats(db, pet, mood=15, satiety=-5, stamina=-5)

# ==================
# Exercise
# ==================
@app.post("/users/{user_id}/exercise", response_model=schemas.Pet, tags=["Exercise"])
def log_exercise(user_id: int, log: schemas.ExerciseLogCreate, db: Session = Depends(get_db)):
    """
    Log an exercise session.
    
    Pass in the exercise type, duration, and volume (scalar).
    The server will automatically calculate growth points, strength,
    stamina cost, etc., and return the updated pet status.
    """
    updated_pet = crud.log_exercise(db, user_id, log)
    if updated_pet is None:
        raise HTTPException(status_code=404, detail="User or pet not found")
    return updated_pet

# ==================
# Daily Quests
# ==================
@app.get("/users/{user_id}/quests", response_model=List[schemas.UserQuest], tags=["Quests"])
def get_daily_quests(user_id: int, db: Session = Depends(get_db)):
    """
    Get the user's daily quest list.
    
    If quests for the day have not been generated, this will create them.
    """
    quests = crud.get_or_create_daily_quests(db, user_id)
    return quests

@app.post("/users/{user_id}/quests/{user_quest_id}/complete", response_model=schemas.Pet, tags=["Quests"])
def complete_daily_quest(user_id: int, user_quest_id: int, db: Session = Depends(get_db)):
    """
    Report a specific quest as complete.
    
    The server marks the quest as complete and applies the rewards
    (updating the pet's status).
    """
    # Note: In this version, calling the API marks it as complete.
    # A future version could have the server auto-complete quests
    # based on events like `log_exercise`.
    updated_pet = crud.complete_quest(db, user_id, user_quest_id)
    if updated_pet is None:
        raise HTTPException(status_code=404, detail="Quest not found or already completed")
    return updated_pet

# ==================
# Travel (Breakthrough)
# ==================
@app.get("/travel/attractions", response_model=List[schemas.Attraction], tags=["Travel"])
def get_all_attractions(db: Session = Depends(get_db)):
    """
    Get all available travel attractions (Placeholders).
    """
    return db.query(models.Attraction).all()

@app.post("/users/{user_id}/travel/start", response_model=schemas.Attraction, tags=["Travel"])
def start_travel_quest(user_id: int, db: Session = Depends(get_db)):
    """
    Start a "breakthrough" quest.
    
    1. Checks if the pet has reached the max level (currently 20).
    2. If so, assigns a random Taipei attraction as the quest target.
    """
    pet = crud.get_pet_by_user_id(db, user_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    if pet.level < crud.MAX_LEVEL:
        raise HTTPException(
            status_code=400, 
            detail=f"Pet has not reached max level {crud.MAX_LEVEL}. Cannot start breakthrough quest."
        )

    attraction = crud.get_random_attraction(db)
    if not attraction:
        raise HTTPException(status_code=500, detail="No travel attractions available")
        
    # A "TravelQuest" record could be created here.
    # For now, just return the attraction.
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
        schemas.LeaderboardEntry(username=username, value=pet.level)
        for pet, username in leaderboard_data
    ]