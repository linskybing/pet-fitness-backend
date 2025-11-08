"""
Test script to demonstrate the new pet growth system
Run after starting the server with: python -m app.main
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def print_response(title, response):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, default=str))

def test_new_system():
    # 1. Create a user
    print("\n1. Creating a new user...")
    response = requests.post(f"{BASE_URL}/users/", json={
        "username": "demo_user",
        "email": "demo@example.com",
        "password": "demo123"
    })
    print_response("User Created", response)
    user_id = response.json()["id"]
    
    # 2. Get initial pet status
    response = requests.get(f"{BASE_URL}/users/{user_id}/pet")
    print_response("Initial Pet Status", response)
    print(f"Note: strength=0, stamina=100, mood=0, stage=EGG")
    
    # 3. Log exercise (5 minutes = 300 seconds = 30 strength points)
    print("\n2. Logging exercise (5 minutes)...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
        "exercise_type": "Running",
        "duration_seconds": 300,
        "volume": 5.0
    })
    print_response("After Exercise", response)
    print(f"Note: strength should be 30, mood should be 5")
    
    # 4. Log more exercise to level up (20 minutes total)
    print("\n3. Logging more exercise (15 more minutes to reach 20 min total)...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
        "exercise_type": "Running",
        "duration_seconds": 900,  # 15 minutes
        "volume": 15.0
    })
    print_response("After More Exercise", response)
    print(f"Note: Should be level 1, strength=120 would trigger level up to level 2")
    
    # 5. Get pet status
    response = requests.get(f"{BASE_URL}/users/{user_id}/pet")
    pet = response.json()
    print_response("Current Pet Status", response)
    
    # 6. Exercise until reaching level 5
    print("\n4. Exercising to reach level 5 (need 120*4=480 more seconds = 48 strength points)...")
    for i in range(4):
        print(f"   Exercise session {i+1}/4...")
        response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
            "exercise_type": "Running",
            "duration_seconds": 1200,  # 20 minutes each
            "volume": 20.0
        })
        if response.json().get("breakthrough_required"):
            print(f"   ⚠️ BREAKTHROUGH REQUIRED!")
            break
    
    response = requests.get(f"{BASE_URL}/users/{user_id}/pet")
    print_response("After Reaching Level 5", response)
    print(f"Note: Should be level 5, breakthrough_required=True, strength blocked at 0")
    
    # 7. Try to exercise without breakthrough
    print("\n5. Attempting to exercise without breakthrough...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
        "exercise_type": "Running",
        "duration_seconds": 600,
        "volume": 10.0
    })
    print_response("Exercise Blocked", response)
    print(f"Note: breakthrough_required=True, strength gains should be 0")
    
    # 8. Get random attraction
    print("\n6. Getting random attraction for breakthrough...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/travel/start")
    print_response("Random Attraction", response)
    
    # 9. Complete breakthrough
    print("\n7. Completing breakthrough...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/travel/breakthrough")
    print_response("Breakthrough Completed", response)
    print(f"Note: stage should change from EGG (0) to CHICK (1)")
    
    # 10. Exercise after breakthrough
    print("\n8. Exercising after breakthrough...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/exercise", json={
        "exercise_type": "Running",
        "duration_seconds": 600,
        "volume": 10.0
    })
    print_response("Exercise After Breakthrough", response)
    print(f"Note: strength gains should work now, breakthrough_required=False")
    
    # 11. Test daily check (simulate not exercising enough)
    print("\n9. Testing daily check...")
    response = requests.post(f"{BASE_URL}/users/{user_id}/daily-check")
    print_response("Daily Check Result", response)
    
    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

if __name__ == "__main__":
    try:
        test_new_system()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running!")
        print("Start the server with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"Error: {e}")
