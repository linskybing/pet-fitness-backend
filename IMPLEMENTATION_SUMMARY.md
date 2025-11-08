# Pet Growth System Updates - Implementation Summary

## Changes Implemented

### 1. Removed Fields

- **Removed `growth_points`**: No longer used for leveling
- **Removed `satiety`**: Hunger/feeding system removed

### 2. Updated Pet Model (`models.py`)

**New/Modified Fields:**

- `strength`: Now 0-120 (resets after level up), default 0
- `stamina`: 0-100 range, default 100 (increased from 20)
- `mood`: Starts at 0 (changed from 50)
- `breakthrough_completed`: Boolean flag for tracking breakthrough status
- `last_daily_check`: DateTime for tracking daily mood checks

### 3. New Leveling System

**Strength-Based Leveling:**

- 10 seconds of exercise = 1 strength point
- 120 strength points = 1 level (20 minutes of exercise)
- Strength resets to 0 after leveling up
- Max level increased to 25

**Breakthrough System:**

- At levels 5, 10, 15, 20: Pet needs breakthrough to continue
- Without breakthrough: strength gains are blocked (set to 0)
- Frontend should show pop-up warning when breakthrough required
- Complete breakthrough by calling `/users/{user_id}/travel/breakthrough`

### 4. Stage Evolution System (Updated)

Stages now only change AFTER breakthrough completion:

- Level 1-4: EGG
- Level 5+ (after lv5 breakthrough): CHICK
- Level 10+ (after lv10 breakthrough): CHICKEN
- Level 15+ (after lv15 breakthrough): BIG_CHICKEN
- Level 20+ (after lv20 breakthrough): BUFF_CHICKEN

### 5. New Mood System

**Mood Mechanics:**

- Initial value: 0 (changed from 50)
- Increases with exercise (+5 per session)
- Daily check at 00:00 (or login):
  - If yesterday's exercise < 10 minutes (60 strength points) AND stamina > 0:
    - Mood decreases by 10
  - If mood reaches 0 AND strength > 0:
    - Strength decreases by 10
  - If stamina is 0: No mood decrease (already exercised enough)

### 6. New API Endpoints

#### Daily Check

```
POST /users/{user_id}/daily-check
```

Performs daily mood check based on yesterday's exercise.

**Response:**

```json
{
  "pet": {...},
  "already_checked": false,
  "met_requirement": true
}
```

#### Complete Breakthrough

```
POST /users/{user_id}/travel/breakthrough
```

Completes breakthrough to continue leveling.

**Response:**

```json
{
  "success": true,
  "pet": {...},
  "message": "Breakthrough completed!"
}
```

#### Start Travel (Get Random Attraction)

```
POST /users/{user_id}/travel/start
```

Gets a random attraction for breakthrough quest.

### 7. Modified API Responses

#### Exercise Logging

```
POST /users/{user_id}/exercise
```

Now returns:

```json
{
  "pet": {...},
  "breakthrough_required": false
}
```

The `breakthrough_required` flag indicates if user needs to complete breakthrough.

#### Quest Completion

```
POST /users/{user_id}/quests/{user_quest_id}/complete
```

Now returns same format as exercise logging with `breakthrough_required` flag.

### 8. Updated Quest Rewards

Quest templates updated to remove growth_points and satiety rewards:

- Daily Check-in: +5 mood, +10 stamina
- Complete 1 Exercise: +20 strength, +10 stamina
- Full of Energy: +50 strength, +10 mood

### 9. Database Migration Required

**IMPORTANT:** The database schema has changed. You need to either:

**Option A: Reset Database (Development)**

```bash
python reset_database.py
```

**Option B: Manual Migration (Production)**
Run these SQL commands:

```sql
-- Remove old columns
ALTER TABLE pets DROP COLUMN growth_points;
ALTER TABLE pets DROP COLUMN satiety;

-- Update existing columns
ALTER TABLE pets ALTER COLUMN strength SET DEFAULT 0;
ALTER TABLE pets ALTER COLUMN stamina SET DEFAULT 100;
ALTER TABLE pets ALTER COLUMN mood SET DEFAULT 0;

-- Add new columns
ALTER TABLE pets ADD COLUMN breakthrough_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE pets ADD COLUMN last_daily_check TIMESTAMP WITH TIME ZONE;

-- Update quest table
ALTER TABLE quests DROP COLUMN reward_growth;
ALTER TABLE quests DROP COLUMN reward_satiety;

-- Update existing pets to new defaults
UPDATE pets SET 
  strength = 0,
  stamina = 100,
  mood = 0,
  breakthrough_completed = FALSE;
```

## Usage Examples

### 1. Exercise Flow

```python
# User exercises for 5 minutes (300 seconds)
POST /users/1/exercise
{
  "exercise_type": "Running",
  "duration_seconds": 300,
  "volume": 5.0
}

# Response:
{
  "pet": {
    "strength": 30,  # 300 seconds / 10 = 30 points
    "level": 1,
    "stamina": 90,   # -10 per exercise
    "mood": 5        # +5 per exercise
  },
  "breakthrough_required": false
}
```

### 2. Level Up Example

```python
# User has 110 strength, exercises for 2 minutes (120 seconds)
# This gives 12 more points = 122 total
# 122 >= 120, so level up!
{
  "pet": {
    "strength": 2,   # 122 - 120 = 2 remaining
    "level": 2,      # Level increased
    "stamina": 100,  # Reset to full on level up
    "mood": 15       # +10 bonus from level up
  },
  "breakthrough_required": false
}
```

### 3. Breakthrough Required

```python
# User reaches level 5
{
  "pet": {
    "strength": 0,
    "level": 5,
    "stage": 0,  # Still EGG, needs breakthrough
    "breakthrough_completed": false
  },
  "breakthrough_required": true  # Frontend should show warning
}

# After calling POST /users/1/travel/breakthrough
{
  "success": true,
  "pet": {
    "level": 5,
    "stage": 1,  # Now CHICK!
    "breakthrough_completed": true
  },
  "message": "Breakthrough completed!"
}
```

### 4. Daily Check

```python
# User didn't exercise enough yesterday
POST /users/1/daily-check

{
  "pet": {
    "mood": 40,  # Decreased from 50
    "strength": 50
  },
  "already_checked": false,
  "met_requirement": false
}

# If mood reaches 0 and strength > 0
{
  "pet": {
    "mood": 0,
    "strength": 40  # Decreased from 50
  },
  "already_checked": false,
  "met_requirement": false
}
```

## Frontend Integration Notes

1. **Breakthrough Warning**: When `breakthrough_required: true`, show a pop-up warning that the user needs to complete a breakthrough to continue gaining strength.

2. **Daily Check**: Call `/users/{user_id}/daily-check` on app startup or at 00:00 each day.

3. **Strength Bar**: Display strength as a progress bar (0-120), showing progress toward next level.

4. **Stage Evolution**: Stage only changes AFTER breakthrough completion, not automatically at level milestones.

5. **Mood Indicator**: Show mood value (0-100) with warning if it's getting low.

## Constants Reference

```python
STRENGTH_PER_LEVEL = 120      # Points needed per level
MIN_DAILY_STRENGTH = 60       # Minimum daily requirement (10 minutes)
MAX_LEVEL = 25                # Maximum achievable level
BREAKTHROUGH_LEVELS = [5, 10, 15, 20]  # Levels requiring breakthrough
```
