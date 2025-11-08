"""
Migration script to add daily_steps to Pet table and steps to ExerciseLog table
Run this after the models have been updated
"""
from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URL
import os

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        # Add daily_steps column to pets table
        try:
            conn.execute(text("""
                ALTER TABLE pets 
                ADD COLUMN IF NOT EXISTS daily_steps INTEGER DEFAULT 0
            """))
            print("✓ Added daily_steps column to pets table")
        except Exception as e:
            print(f"Note: daily_steps column might already exist: {e}")
        
        # Add steps column to exercise_logs table
        try:
            conn.execute(text("""
                ALTER TABLE exercise_logs 
                ADD COLUMN IF NOT EXISTS steps INTEGER DEFAULT 0
            """))
            print("✓ Added steps column to exercise_logs table")
        except Exception as e:
            print(f"Note: steps column might already exist: {e}")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
