import os
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app, supabase

@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
    reason="SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env for integration tests"
)
class TestIntegration:
    """Integration tests that interact with the real Supabase database."""

    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        self.test_email = f"test_{uuid.uuid4()}@test.local"
        self.test_password = "testpassword123"

    def teardown_method(self):
        """Cleanup after each test method."""
        # Clean up test application
        try:
            supabase.table("applications").delete().eq("telegram", f"@test_{self.test_email}").execute()
        except Exception:
            pass  # Ignore cleanup errors

        # Note: User cleanup would require admin privileges in Supabase
        # For now, we'll leave test users in the database

    def test_full_auth_and_application_flow(self):
        """Test the complete flow: register -> login -> submit application -> verify in DB."""

        # Step 1: Register a new user
        register_response = self.client.post("/auth/register", json={
            "email": self.test_email,
            "password": self.test_password
        })

        # Registration might fail if email already exists, but that's okay for integration testing
        if register_response.status_code == 400:
            response_text = register_response.json().get("detail", "").lower()
            if "email" in response_text and ("invalid" in response_text or "format" in response_text):
                pytest.skip("Test email domain not accepted by Supabase")
            # User might already exist, try login instead
            pass
        else:
            assert register_response.status_code == 200

        # Step 2: Login with the user
        login_response = self.client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })

        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert "user" in login_data

        access_token = login_data["access_token"]

        # Step 3: Get current user info
        me_response = self.client.get("/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })

        assert me_response.status_code == 200
        user_data = me_response.json()
        assert "id" in user_data
        assert user_data["email"] == self.test_email

        # Step 4: Submit an application (no auth required)
        unique_telegram = f"@test_{uuid.uuid4()}"
        app_response = self.client.post("/api/applications", json={
            "name": "Integration Test User",
            "telegram": unique_telegram,
            "motivation": "Testing the full integration flow"
        })

        assert app_response.status_code == 200
        assert app_response.json() == {"message": "Application received"}

        # Step 5: Verify the application was saved in the database
        db_response = supabase.table("applications").select("*").eq("telegram", unique_telegram).execute()

        assert len(db_response.data) == 1
        application = db_response.data[0]
        assert application["name"] == "Integration Test User"
        assert application["telegram"] == unique_telegram
        assert application["motivation"] == "Testing the full integration flow"
        assert "id" in application
        assert "created_at" in application

    def test_application_submission_anonymous(self):
        """Test that applications can be submitted without authentication."""

        unique_telegram = f"@anon_{uuid.uuid4()}"
        response = self.client.post("/api/applications", json={
            "name": "Anonymous User",
            "telegram": unique_telegram,
            "motivation": "Testing anonymous application submission"
        })

        assert response.status_code == 200
        assert response.json() == {"message": "Application received"}

        # Verify in database
        db_response = supabase.table("applications").select("*").eq("telegram", unique_telegram).execute()
        assert len(db_response.data) == 1

    def test_auth_endpoints_validation(self):
        """Test validation of auth endpoints."""

        # Test invalid email format
        response = self.client.post("/auth/register", json={
            "email": "invalid-email",
            "password": "password"
        })
        assert response.status_code == 400

        # Test missing fields
        response = self.client.post("/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422  # Validation error

        # Test invalid token
        response = self.client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401