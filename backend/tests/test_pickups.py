import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# Avoid circular imports in skeleton
# from app.main import app 

def test_pickup_creation_requires_subscription(client: TestClient, db: Session, org_user_token: str):
    """
    Test that an Organization cannot create a pickup without an active subscription.
    """
    # 1. Ensure org has no active subscription
    
    # 2. Hit POST /api/v1/pickups/
    response = client.post(
        "/api/v1/pickups/",
        headers={"Authorization": f"Bearer {org_user_token}"},
        json={
            "waste_type": "GENERAL",
            "waste_weight": 10.5,
            "address": "123 Test St",
            "latitude": 40.7128,
            "longitude": -74.0060,
        }
    )
    
    # 3. Assert 403 Forbidden with specific message
    assert response.status_code == 403
    assert "No active subscription found" in response.json()["detail"]


def test_pickup_creation_enforces_weight_limit(client: TestClient, db: Session, org_user_token: str):
    """
    Test that a pickup is rejected if the waste weight exceeds the plan's limit.
    """
    # Setup: Create active subscription with weight limit of 100kg
    
    # Action: Try to create pickup with 150kg
    response = client.post("/api/v1/pickups/", headers={"Authorization": f"Bearer {org_user_token}"}, json={"waste_weight": 150.0})
    
    # Assert
    assert response.status_code == 403
    assert "Waste weight limit exceeded" in response.json()["detail"]


def test_pickup_creation_enforces_pickup_count_limit(client: TestClient, db: Session, org_user_token: str):
    """
    Test that a pickup is rejected if the org has used all their pickups for the cycle.
    """
    # Setup: Create active subscription with pickup limit of 1, and manually set usage.pickups_used = 1
    
    # Action: Try to create another pickup
    response = client.post("/api/v1/pickups/", headers={"Authorization": f"Bearer {org_user_token}"}, json={})
    
    # Assert
    assert response.status_code == 403
    assert "Pickup limit exceeded" in response.json()["detail"]


def test_expired_subscription_blocks_pickup(client: TestClient, db: Session, org_user_token: str):
    """
    Test that an expired subscription transitions to EXPIRED and blocks the pickup.
    """
    # Setup: Create subscription with end_date in the past
    
    # Action: Try to create pickup
    response = client.post("/api/v1/pickups/", headers={"Authorization": f"Bearer {org_user_token}"}, json={})
    
    # Assert
    assert response.status_code == 403
    assert "Subscription has expired" in response.json()["detail"]


def test_invalid_status_transition_rejected(client: TestClient, db: Session, admin_token: str):
    """
    Test that a COMPLETED pickup cannot be CANCELLED or marked PENDING again.
    """
    # Setup: Create a pickup and forcefully mark it COMPLETED
    pickup_id = 1
    
    # Action: Try to cancel it via PATCH
    response = client.patch(f"/api/v1/pickups/{pickup_id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "CANCELLED"})
    
    # Assert
    assert response.status_code == 400
    assert "Invalid transition" in response.json()["detail"]


def test_driver_access_control(client: TestClient, db: Session, driver_token: str):
    """
    Test that a Driver can only view pickups they are assigned to.
    """
    # Setup: Create Pickup A (unassigned), Pickup B (assigned to Driver 1)
    
    # Action: Driver 1 calls GET /api/v1/pickups/
    response = client.get("/api/v1/pickups/", headers={"Authorization": f"Bearer {driver_token}"})
    
    # Assert
    assert response.status_code == 200
    pickups = response.json()["pickups"]
    assert len(pickups) == 1  # Should only see Pickup B
