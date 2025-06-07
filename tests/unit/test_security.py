import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.security import create_access_token, verify_token_and_get_payload, ALGORITHM
# SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES are also needed for validation against actual values.
# However, if they are loaded from settings, we might need to mock settings or ensure they have test values.
# For unit tests, it's often better to pass them as arguments or use fixed test values if possible.
# Assuming they are global constants in security.py for this test.
from app.core import security as security_module # To access module-level constants if needed
from app.core.exceptions import AuthenticationError

# Use a fixed secret key for testing to ensure reproducibility
TEST_SECRET_KEY = "test_secret_key_for_unit_tests"
TEST_ACCESS_TOKEN_EXPIRE_MINUTES = 15

@pytest.fixture(autouse=True)
def override_security_constants(monkeypatch):
    """Override security constants for test isolation."""
    monkeypatch.setattr(security_module, 'SECRET_KEY', TEST_SECRET_KEY)
    monkeypatch.setattr(security_module, 'ACCESS_TOKEN_EXPIRE_MINUTES', TEST_ACCESS_TOKEN_EXPIRE_MINUTES)

def test_create_access_token():
    data = {"sub": "testuser@example.com"}
    token = create_access_token(data)
    # Decode with the TEST_SECRET_KEY used by the patched create_access_token
    payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser@example.com"
    assert "exp" in payload
    assert "iat" in payload
    # Check if expiry is roughly correct based on TEST_ACCESS_TOKEN_EXPIRE_MINUTES
    expected_exp = datetime.now(timezone.utc) + timedelta(minutes=TEST_ACCESS_TOKEN_EXPIRE_MINUTES)
    # Allow a small delta for execution time
    assert abs(datetime.fromtimestamp(payload["exp"], timezone.utc) - expected_exp) < timedelta(seconds=10)

def test_create_access_token_custom_expiry():
    data = {"sub": "testuser_custom_exp@example.com"}
    custom_delta = timedelta(hours=2)
    token = create_access_token(data, expires_delta=custom_delta)
    payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser_custom_exp@example.com"
    expected_exp = datetime.now(timezone.utc) + custom_delta
    assert abs(datetime.fromtimestamp(payload["exp"], timezone.utc) - expected_exp) < timedelta(seconds=10)

def test_verify_token_and_get_payload_valid():
    data = {"sub": "testuser_valid_verify@example.com"}
    token = create_access_token(data) # Uses patched constants
    payload = verify_token_and_get_payload(token) # Uses patched constants for verification
    assert payload["sub"] == "testuser_valid_verify@example.com"

def test_verify_token_expired():
    # Create a token that expired 1 minute ago
    expired_delta = timedelta(minutes=-1)
    # Use the patched create_access_token which will use TEST_SECRET_KEY and ALGORITHM
    token = create_access_token({"sub": "testuser_expired_verify@example.com"}, expires_delta=expired_delta)

    with pytest.raises(AuthenticationError, match="Token has expired."): # Expecting specific message from security.py
        verify_token_and_get_payload(token)

def test_verify_token_invalid_signature_or_format():
    # Test with a token signed by a different key (conceptually)
    # For this, we can create a token with a different key and try to decode with TEST_SECRET_KEY
    wrong_secret_key = "a_completely_different_secret_key_for_testing"
    data = {"sub": "testuser_wrong_key@example.com"}
    expire = datetime.now(timezone.utc) + timedelta(minutes=TEST_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    token_wrong_key = jwt.encode(to_encode, wrong_secret_key, algorithm=ALGORITHM)

    with pytest.raises(AuthenticationError, match="Could not validate credentials: Signature verification failed."):
        verify_token_and_get_payload(token_wrong_key) # This will use TEST_SECRET_KEY for decoding

    # Test with a malformed token
    invalid_token_format = "this.is.notavalidjwtatall"
    with pytest.raises(AuthenticationError, match="Could not validate credentials: Not enough segments"): # Or other JWTError specific message
        verify_token_and_get_payload(invalid_token_format)

def test_verify_token_missing_sub_claim():
    # Manually encode a token without 'sub' claim using TEST_SECRET_KEY
    payload_no_sub = {"user_id": "test_no_sub_verify"} # Missing 'sub'
    expire = datetime.now(timezone.utc) + timedelta(minutes=TEST_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = payload_no_sub.copy()
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    token_no_sub = jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(AuthenticationError, match="Token missing subject \(sub\) claim"):
        verify_token_and_get_payload(token_no_sub)

def test_verify_token_no_token_provided():
    with pytest.raises(AuthenticationError, match="No token provided."):
        verify_token_and_get_payload("") # Empty token string

# Test case for JWTError that isn't ExpiredSignatureError or a common structure error
@patch("app.core.security.jwt.decode")
def test_verify_token_other_jwt_error(mock_jwt_decode):
    mock_jwt_decode.side_effect = JWTError("Some other JWT processing error")
    with pytest.raises(AuthenticationError, match="Could not validate credentials: Some other JWT processing error"):
        verify_token_and_get_payload("any_token_string")
