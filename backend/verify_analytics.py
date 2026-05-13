import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_unauthorized():
    print("Testing unauthorized access to /analytics/dashboard...")
    response = requests.get(f"{BASE_URL}/analytics/dashboard")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")

if __name__ == "__main__":
    try:
        test_unauthorized()
    except Exception as e:
        print(f"Error connecting to server: {e}")
