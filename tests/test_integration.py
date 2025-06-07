import pytest
from fastapi.testclient import TestClient
from pathlib import Path # For checking backup file path if needed

# This global variable is a simple way to pass the token between tests in a single file.
# For more complex scenarios, consider pytest fixtures or a shared context object (e.g. a class instance).
shared_data = {}

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    # The message in health check was updated in a previous subtask.
    # Let's ensure this matches the current state from `app/routers/health.py`
    assert response.json() == {"status": "OK", "message": "Logging configured! Check console/logs."}

def test_login_and_get_me(client: TestClient):
    """Test user login and fetching user details from /me endpoint."""
    # Using a known mock API key that should be valid based on auth router logic
    # (not empty, not the default placeholder like 'YOUR_GEMINI_API_KEY_HERE')
    login_payload = {"apiKey": "test_integration_gemini_key_12345_valid"} # Make it more unique
    response = client.post("/api/auth/login", json=login_payload)

    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()

    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert "user" in token_data
    assert "id" in token_data["user"]

    shared_data["access_token"] = token_data["access_token"] # Store for subsequent tests

    headers = {"Authorization": f"Bearer {shared_data['access_token']}"}
    response_me = client.get("/api/me", headers=headers)
    assert response_me.status_code == 200, f"/me endpoint failed: {response_me.text}"
    user_data_me = response_me.json()
    assert user_data_me["id"] == token_data["user"]["id"]

def test_data_fetch_fred_gnpca_and_cache(client: TestClient):
    """Test fetching data from FRED (GNPCA series) and caching functionality."""
    if "access_token" not in shared_data:
        pytest.skip("Authentication token not available, skipping data_fetch_and_cache test.")

    headers = {"Authorization": f"Bearer {shared_data['access_token']}"}
    # Using a common public series for FRED that usually does not require an API key.
    fetch_payload = {"source": "fred", "parameters": {"symbol": "GNPCA"}}

    # First fetch - should not be cached initially
    response_fetch1 = client.post("/api/data/fetch", json=fetch_payload, headers=headers)
    assert response_fetch1.status_code == 200, f"First fetch failed: {response_fetch1.text}"
    data1 = response_fetch1.json()
    assert data1["success"] is True
    assert data1["source"] == "fred"
    assert data1["is_cached"] is False, "First fetch should not be from cache"
    assert "data" in data1
    assert data1["data"] is not None, "Data from FRED (GNPCA) should not be None"
    assert "observations" in data1["data"], "FRED data should contain 'observations'"

    # Second fetch - should be retrieved from cache
    response_fetch2 = client.post("/api/data/fetch", json=fetch_payload, headers=headers)
    assert response_fetch2.status_code == 200, f"Second fetch failed: {response_fetch2.text}"
    data2 = response_fetch2.json()
    assert data2["success"] is True
    assert data2["is_cached"] is True, "Second fetch should be from cache"
    assert data2["data"] == data1["data"], "Cached data should be identical to first fetch"

def test_chat_simple_interaction(client: TestClient):
    """Test a simple chat interaction without specific triggers."""
    if "access_token" not in shared_data:
        pytest.skip("Authentication token not available, skipping chat interaction test.")

    headers = {"Authorization": f"Bearer {shared_data['access_token']}"}
    chat_payload = {
        "user_message": "Hello, AI! How are you today?",
        "context": {
            "chat_history": []
            # No file_content, external_data, or selected_modules for a simple greeting.
        }
    }
    response = client.post("/api/chat", json=chat_payload, headers=headers)
    assert response.status_code == 200, f"Chat request failed: {response.text}"
    chat_response_data = response.json()
    assert "reply" in chat_response_data
    assert len(chat_response_data["reply"]) > 0, "AI reply should not be empty for a simple greeting"
    # Note: Actual AI reply content is non-deterministic. Test checks for a non-empty reply.

def test_chat_initial_analysis_trigger(client: TestClient):
    """Test the chat endpoint with 'initial_analysis' trigger action."""
    if "access_token" not in shared_data:
        pytest.skip("Authentication token not available.")

    headers = {"Authorization": f"Bearer {shared_data['access_token']}"}
    payload = {
        "user_message": "This user message is currently used for date_range by the router if not in context.",
        "trigger_action": "initial_analysis",
        "context": {
            "file_content": "Mock Shan Jia Lang post content for testing initial analysis trigger.",
            "date_range_for_analysis": "2023-W50", # Using the dedicated context field
            "external_data": {"example_metric": [{"date": "2023-12-01", "value": "100"}]},
            "selected_modules": ["交易醫生"] # Example module
        }
    }
    response = client.post("/api/chat", json=payload, headers=headers)
    assert response.status_code == 200, f"Initial analysis chat request failed: {response.text}"
    chat_response_data = response.json()
    assert "reply" in chat_response_data
    assert len(chat_response_data["reply"]) > 0, "AI reply for initial analysis should not be empty"
    # Further structural checks on the Markdown reply could be added if a very consistent output is expected.
    assert "A. 週次與日期範圍:" in chat_response_data["reply"], "Initial analysis reply missing section A"
    assert "B. 「善甲狼」核心觀點摘要:" in chat_response_data["reply"], "Initial analysis reply missing section B"

def test_database_backup(client: TestClient, temp_db_path_session: Path): # Use the session DB path
    """Test the database backup endpoint."""
    if "access_token" not in shared_data:
        pytest.skip("Authentication token not available, skipping database backup test.")

    headers = {"Authorization": f"Bearer {shared_data['access_token']}"}
    response = client.post("/api/db/backup", headers=headers)
    assert response.status_code == 200, f"Database backup request failed: {response.text}"
    backup_data = response.json()
    assert backup_data["success"] is True
    assert "message" in backup_data
    assert "backup_path" in backup_data
    assert backup_data["backup_path"] is not None

    # Verify the backup file was created in the same directory as the temp DB
    backup_file = Path(backup_data["backup_path"])
    assert backup_file.exists(), f"Backup file {backup_file} does not exist."
    assert backup_file.parent == temp_db_path_session.parent, "Backup file not in the expected directory."
    # Clean up the created backup file to keep test environment clean
    if backup_file.exists():
        backup_file.unlink()

# Potential tests to add:
# - Test with invalid token for protected endpoints (expect 401)
# - Test data fetch for a FRED symbol that requires API key (if FRED_API_KEY is set for tests)
# - Test chat with search intent
# - Test chat 'final_report_preview' trigger
# - Test validation errors for ChatRequest (e.g., missing file_content for initial_analysis)
# - Test for specific error codes on known error conditions (e.g., invalid API key for login)
