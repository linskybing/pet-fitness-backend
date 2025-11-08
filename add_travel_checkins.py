"""
Migration script to add travel_checkins table for location-based quests.
Run this script to update the database schema.
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'travel_checkins'
            );
        """))
        table_exists = result.scalar()
        
        if table_exists:
            print("✓ travel_checkins table already exists, skipping creation")
            return
        
        print("Creating travel_checkins table...")
        
        # Create travel_checkins table
        conn.execute(text("""
            CREATE TABLE travel_checkins (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                quest_id VARCHAR NOT NULL,
                completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                lat FLOAT NOT NULL,
                lng FLOAT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """))
        
        # Create indexes for better query performance
        conn.execute(text("""
            CREATE INDEX idx_travel_checkins_user_id ON travel_checkins(user_id);
        """))
        
        conn.execute(text("""
            CREATE INDEX idx_travel_checkins_quest_id ON travel_checkins(quest_id);
        """))
        
        conn.commit()
        print("✓ Successfully created travel_checkins table and indexes")

if __name__ == "__main__":
    try:
        migrate()
        print("\n✓ Migration completed successfully!")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        raise
