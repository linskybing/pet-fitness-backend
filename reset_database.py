"""
Database reset script - Drops all tables and recreates them with seed data
WARNING: This will delete all existing data!
"""
from app.database import engine, SessionLocal
from app import models, crud, schemas

def reset_database():
    print("WARNING: This will delete ALL data in the database!")
    print("Dropping all tables...")
    
    # Drop all tables
    models.Base.metadata.drop_all(bind=engine)
    print("All tables dropped")
    
    print("Creating all tables...")
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    print("All tables created")
    
    print("Seeding initial data...")
    # Seed initial data
    db = SessionLocal()
    try:
        # Seed attractions
        crud.seed_attractions(db)
        print("Attractions seeded")
        
        # Seed daily quest templates
        for quest_template in crud.QUEST_TEMPLATES:
            q = db.query(models.Quest).filter(models.Quest.title == quest_template["title"]).first()
            if not q:
                q = models.Quest(**quest_template)
                db.add(q)
        db.commit()
        print("Quest templates seeded")
        
        # Create default user with id="1" and a pet
        default_user = schemas.UserCreate(
            user_id="1",
            pet_name="預設小雞"
        )
        created_user = crud.create_user(db, default_user)
        print(f"Default user created: id={created_user.id}, pet_name={created_user.pet.name}")
        
        print("\nDatabase reset complete!")
        print(f"Default user id: {created_user.id}")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_database()
