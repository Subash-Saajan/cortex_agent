import requests
import json
import uuid
import time

# Configuration - Update this to your deployed API URL or localhost
BASE_URL = "https://api.cortex.subashsaajan.site" 
# BASE_URL = "http://localhost:8000"

def log_step(msg):
    print(f"\n{'='*20} {msg} {'='*20}")

def test_user_flow(user_email, name, position, personalization, test_fact, chat_query):
    # 1. Create a fake UUID for testing (In reality, this comes from Google OAuth)
    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_email))
    print(f"Testing for User: {name} (ID: {user_id})")

    # 2. Setup User
    log_step(f"1. Setting up profile for {name}")
    setup_data = {
        "user_id": user_id,
        "name": name,
        "job_title": position,
        "main_goal": f"Manage my schedule as a {position}",
        "work_hours": "9 AM - 5 PM",
        "personalization": personalization
    }
    res = requests.post(f"{BASE_URL}/api/auth/setup", json=setup_data)
    print(f"Setup status: {res.status_code} - {res.json()}")

    # 3. Chat & Store Memory
    log_step(f"2. Sending first message (Storing: {test_fact})")
    chat_data = {
        "user_id": user_id,
        "message": f"Hi, please remember that {test_fact}"
    }
    res = requests.post(f"{BASE_URL}/api/chat", json=chat_data)
    response_data = res.json()
    conv_id = response_data.get("conversation_id")
    print(f"AI Response: {response_data.get('response')}")

    # 4. Verify Personalization & Memory Recall
    log_step(f"3. Verifying Personalization and Memory Recall")
    chat_data = {
        "user_id": user_id,
        "conversation_id": conv_id,
        "message": chat_query
    }
    res = requests.post(f"{BASE_URL}/api/chat", json=chat_data)
    print(f"AI Response (matching '{personalization}'):\n---\n{res.json().get('response')}\n---")

    return user_id

if __name__ == "__main__":
    print(f"Cortex Multi-User Feature Demonstration")
    print(f"Target API: {BASE_URL}")

    # USER 1: Alice (Technical Student)
    alice_id = test_user_flow(
        user_email="alice@student.com",
        name="Alice",
        position="Computer Science Student",
        personalization="Be extremely concise. Use technical terms. No fluff.",
        test_fact="my favorite programming language is Rust.",
        chat_query="What is my favorite language? Give me a 1-sentence explanation of why it's good."
    )

    print("\n\n" + "#"*60 + "\n\n")

    # USER 2: Bob (Business Owner)
    bob_id = test_user_flow(
        user_email="bob@business.com",
        name="Bob",
        position="CEO of TechCorp",
        personalization="Be very formal and extremely polite. Address me as 'Sir'. Use elaborate sentences.",
        test_fact="my company is launching a new AI product next Tuesday.",
        chat_query="When is my company's launch? Also, express your enthusiasm about it."
    )

    log_step("Final Verification: Profile Persistence Check")
    # Verify profile data for Alice still exists
    res = requests.get(f"{BASE_URL}/api/auth/user/{alice_id}")
    profile = res.json()
    print(f"Alice's Profile still has personalization: '{profile.get('personalization')}'")
    
    # Wipe Bob's chat but verify profile stays
    log_step("Wiping Bob's chat data but preserving profile...")
    requests.delete(f"{BASE_URL}/api/user/data/{bob_id}")
    res = requests.get(f"{BASE_URL}/api/auth/user/{bob_id}")
    profile = res.json()
    print(f"Bob's data wiped, but Name '{profile.get('name')}' and Personalization '{profile.get('personalization')}' are STILL HERE.")
