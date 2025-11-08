"""
Add daily tracking columns to pets table
Run this script if you don't want to reset the entire database
"""
from app.database import engine
from sqlalchemy import text

def add_daily_tracking_columns():
    print("Adding daily tracking columns to pets table...")
    
    try:
        with engine.connect() as conn:
            # Add daily_exercise_seconds column
            try:
                conn.execute(text("""
                    ALTER TABLE pets 
                    ADD COLUMN daily_exercise_seconds INTEGER DEFAULT 0
                """))
                print("✓ Column daily_exercise_seconds added")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("✓ Column daily_exercise_seconds already exists")
                else:
                    raise
            
            # Add last_reset_date column
            try:
                conn.execute(text("""
                    ALTER TABLE pets 
                    ADD COLUMN last_reset_date TIMESTAMP WITH TIME ZONE
                """))
                print("✓ Column last_reset_date added")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("✓ Column last_reset_date already exists")
                else:
                    raise
            
            conn.commit()
            print("\n✓ Migration completed successfully!")
                
    except Exception as e:
        print(f"Error: {e}")
        print("\nIf you see an error, please run: python reset_database.py")

if __name__ == "__main__":
    add_daily_tracking_columns()
