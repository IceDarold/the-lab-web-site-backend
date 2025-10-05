import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_register_success(client, mocker):
    mock_response = mocker.MagicMock()
    mock_response.user.dict.return_value = {"id": "123", "email": "test@example.com"}
    mocker.patch("main.supabase.auth.sign_up", return_value=mock_response)

    response = client.post("/auth/register", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 200
    assert "message" in response.json()

def test_register_failure(client, mocker):
    mocker.patch("main.supabase.auth.sign_up", side_effect=Exception("Error"))

    response = client.post("/auth/register", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 400

def test_login_success(client, mocker):
    mock_session = mocker.MagicMock()
    mock_session.access_token = "access_token"
    mock_session.refresh_token = "refresh_token"
    mock_response = mocker.MagicMock()
    mock_response.session = mock_session
    mock_response.user.dict.return_value = {"id": "123", "email": "test@example.com"}
    mocker.patch("main.supabase.auth.sign_in_with_password", return_value=mock_response)

    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data

def test_login_failure(client, mocker):
    mocker.patch("main.supabase.auth.sign_in_with_password", side_effect=Exception("Invalid credentials"))

    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 401

def test_me_success(client, mocker):
    mock_user_response = mocker.MagicMock()
    mock_user_response.user = {"id": "123", "email": "test@example.com"}
    mocker.patch("main.supabase.auth.get_user", return_value=mock_user_response)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"id": "123", "email": "test@example.com"}

def test_me_failure(client, mocker):
    mocker.patch("main.supabase.auth.get_user", side_effect=Exception("Invalid token"))

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401

def test_submit_application(client, mocker):
    mock_table = mocker.MagicMock()
    mock_insert = mocker.MagicMock()
    mock_execute = mocker.MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute
    mocker.patch("main.supabase.table", return_value=mock_table)

    # Mock the notification function
    mocker.patch("main.send_notification_to_users_sync")

    response = client.post("/api/applications", json={"name": "Test", "telegram": "@test", "motivation": "Test motivation"})
    assert response.status_code == 200
    assert response.json() == {"message": "Application received"}