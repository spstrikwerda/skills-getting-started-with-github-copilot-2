"""
Test suite for Mergington High School Activities API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
    }
    
    # Reset to original state
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that getting activities returns 200 status"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that getting activities returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that activities contain expected keys"""
        response = client.get("/activities")
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test successful signup for an existing activity"""
        response = client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant_to_list(self, client):
        """Test that signup actually adds participant to the activity"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post("/activities/Nonexistent Club/signup?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Activity not found"
    
    def test_duplicate_signup_rejected(self, client):
        """Test that signing up twice for the same activity is rejected"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"]
    
    def test_signup_with_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post("/activities/Programming%20Class/signup?email=test@mergington.edu")
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_from_activity(self, client):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_unregister_removes_participant_from_list(self, client):
        """Test that unregistering actually removes participant from the activity"""
        email = "michael@mergington.edu"
        client.delete(f"/activities/Chess Club/unregister?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete("/activities/Nonexistent Club/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_when_not_registered(self, client):
        """Test unregistering when student is not registered for the activity"""
        email = "notregistered@mergington.edu"
        response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_with_url_encoded_activity_name(self, client):
        """Test unregister with URL-encoded activity name"""
        email = "emma@mergington.edu"  # Already in Programming Class
        response = client.delete(f"/activities/Programming%20Class/unregister?email={email}")
        assert response.status_code == 200


class TestWorkflow:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow: signup -> verify -> unregister -> verify"""
        email = "workflow@mergington.edu"
        activity = "Gym Class"
        
        # Initial state - not registered
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify registration
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify unregistration
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]
    
    def test_cannot_signup_after_duplicate(self, client):
        """Test that after a failed duplicate signup, the participant list is unchanged"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()["Chess Club"]["participants"])
        
        # Try to signup again
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 400
        
        # Verify count hasn't changed
        response = client.get("/activities")
        final_count = len(response.json()["Chess Club"]["participants"])
        assert initial_count == final_count
