"""
Test script for daily exercise tracking and steps counting
"""
import requests
import json

BASE_URL = "http://localhost:8080"

def test_daily_tracking():
    user_id = "test_user_daily_123"
    
    # 1. Create a test user
    print("1. Creating test user...")
    response = requests.post(f"{BASE_URL}/users/", json={
        "user_id": user_id,
        "pet_name": "測試雞"
    })
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        pet = response.json().get("pet")
        print(f"   Initial daily_exercise_seconds: {pet.get('daily_exercise_seconds', 0)}")
        print(f"   Initial daily_steps: {pet.get('daily_steps', 0)}")
    
    # 2. Log a walking exercise with steps
    print("\n2. Logging walking exercise (60 seconds, 100 steps)...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
        "exercise_type": "Walking",
        "duration_seconds": 60,
        "volume": 1.0,
        "steps": 100
    })
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        pet = result.get("pet")
        print(f"   Daily exercise time: {pet.get('daily_exercise_seconds', 0)} seconds")
        print(f"   Daily steps: {pet.get('daily_steps', 0)} steps")
    
    # 3. Log another exercise
    print("\n3. Logging running exercise (120 seconds, 200 steps)...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
        "exercise_type": "Running",
        "duration_seconds": 120,
        "volume": 2.0,
        "steps": 200
    })
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        pet = result.get("pet")
        print(f"   Daily exercise time: {pet.get('daily_exercise_seconds', 0)} seconds")
        print(f"   Daily steps: {pet.get('daily_steps', 0)} steps")
    
    # 4. Get pet status
    print("\n4. Getting pet status...")
    response = requests.get(f"{BASE_URL}/users/{user_id}/pet")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        pet = response.json()
        print(f"   Pet name: {pet.get('name')}")
        print(f"   Level: {pet.get('level')}")
        print(f"   Daily exercise time: {pet.get('daily_exercise_seconds', 0)} seconds")
        print(f"   Daily steps: {pet.get('daily_steps', 0)} steps")
        print(f"   Last reset date: {pet.get('last_reset_date', 'N/A')}")
    
    # 5. Perform daily check (should reset daily stats)
    print("\n5. Performing daily check (simulating next day login)...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/daily-check")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        pet = result.get("pet")
        print(f"   Already checked today: {result.get('already_checked', False)}")
        print(f"   Daily exercise time after reset: {pet.get('daily_exercise_seconds', 0)} seconds")
        print(f"   Daily steps after reset: {pet.get('daily_steps', 0)} steps")
        print(f"   Last reset date: {pet.get('last_reset_date', 'N/A')}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    print("Testing Daily Exercise Tracking and Steps Counting")
    print("=" * 60)
    test_daily_tracking()
