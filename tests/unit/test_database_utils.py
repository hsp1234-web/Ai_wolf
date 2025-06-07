import pytest
from unittest.mock import patch, MagicMock, call # Added call for checking multiple calls
from app.db.database import hash_params, get_cached_data, set_cached_data, DEFAULT_CACHE_TTL_SECONDS, initialize_cache_table # Added initialize_cache_table
from datetime import datetime, timedelta, timezone
import json
import sqlite3 # To simulate sqlite3.Error

def test_hash_params_consistency_and_order_insensitivity():
    """Tests that hash_params produces consistent hashes for identical content regardless of initial order."""
    params1 = {"source": "fred", "symbol": "GDP", "frequency": "q"}
    params2 = {"symbol": "GDP", "frequency": "q", "source": "fred"} # Same params, different order
    assert hash_params(params1) == hash_params(params2), "Hashes should be identical for same parameters in different order."

def test_hash_params_value_sensitivity():
    """Tests that hash_params produces different hashes for different parameter values."""
    params1 = {"symbol": "GDP", "value": 100}
    params3 = {"symbol": "GDP", "value": 200} # Different value
    assert hash_params(params1) != hash_params(params3), "Hashes should differ for different parameter values."

def test_hash_params_key_sensitivity():
    """Tests that hash_params produces different hashes for different parameter keys."""
    params1 = {"symbol": "GDP", "key_a": "val"}
    params4 = {"symbol": "GDP", "key_b": "val"} # Different key name
    assert hash_params(params1) != hash_params(params4), "Hashes should differ for different parameter keys."

# --- Tests for caching logic (get_cached_data, set_cached_data, initialize_cache_table) ---

@patch("app.db.database.get_db_connection")
def test_get_cached_data_hit_and_valid(mock_get_conn: MagicMock):
    """Test cache hit with valid, non-expired data."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    source = "test_source_hit"
    params = {"query": "test_query"}
    expected_data = {"result": "some cached data"}
    data_json = json.dumps(expected_data)
    # expires_at is one hour in the future
    expires_at_future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Simulate database returning a row
    mock_cursor.fetchone.return_value = {"expires_at": expires_at_future, "data": data_json}

    cached_result = get_cached_data(source, params)

    assert cached_result == expected_data
    expected_hash = hash_params(params)
    mock_cursor.execute.assert_called_once_with(
        'SELECT data, expires_at FROM external_data_cache WHERE source = ? AND params_hash = ?',
        (source, expected_hash)
    )

@patch("app.db.database.get_db_connection")
def test_get_cached_data_miss_no_entry(mock_get_conn: MagicMock):
    """Test cache miss when no entry is found in the database."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None # Simulate DB returns no row

    cached_result = get_cached_data("test_source_miss", {"p": "another_query"})
    assert cached_result is None
    mock_cursor.execute.assert_called_once() # Ensure it tried to query

@patch("app.db.database.get_db_connection")
def test_get_cached_data_expired_entry_deleted(mock_get_conn: MagicMock):
    """Test cache miss due to expired data, and ensure the expired entry is deleted."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    source = "test_source_expired_delete"
    params = {"p": "expired_query"}
    expected_hash = hash_params(params)
    data_json = json.dumps({"result": "old data"})
    # expires_at is one hour in the past
    expires_at_past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    mock_cursor.fetchone.return_value = {"expires_at": expires_at_past, "data": data_json}

    cached_result = get_cached_data(source, params)
    assert cached_result is None

    # Check that SELECT was called, then DELETE was called for the expired entry
    expected_calls = [
        call('SELECT data, expires_at FROM external_data_cache WHERE source = ? AND params_hash = ?', (source, expected_hash)),
        call('DELETE FROM external_data_cache WHERE source = ? AND params_hash = ?', (source, expected_hash))
    ]
    mock_cursor.execute.assert_has_calls(expected_calls, any_order=False)
    mock_conn.commit.assert_called_once() # Commit after delete

@patch("app.db.database.get_db_connection")
def test_set_cached_data_success(mock_get_conn: MagicMock):
    """Test successfully setting data into the cache."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    source = "test_set_source_ok"
    params = {"query": "new_data_query"}
    data_to_cache = {"result": "this is new data"}
    ttl = 600 # 10 minutes

    set_cached_data(source, params, data_to_cache, ttl_seconds=ttl)

    mock_cursor.execute.assert_called_once()
    args, kwargs = mock_cursor.execute.call_args
    assert "INSERT OR REPLACE INTO external_data_cache" in args[0]
    # Check passed values to execute (index 1 of args tuple)
    assert args[1][0] == source
    assert args[1][1] == hash_params(params)
    assert args[1][2] == json.dumps(data_to_cache)
    # Check that timestamp and expires_at are ISO format strings
    now_utc_for_check = datetime.now(timezone.utc)
    timestamp_in_call = datetime.fromisoformat(args[1][3])
    expires_at_in_call = datetime.fromisoformat(args[1][4])

    assert abs(timestamp_in_call - now_utc_for_check) < timedelta(seconds=5)
    expected_expires_at = now_utc_for_check + timedelta(seconds=ttl)
    assert abs(expires_at_in_call - expected_expires_at) < timedelta(seconds=5)

    mock_conn.commit.assert_called_once()

@patch("app.db.database.get_db_connection")
def test_get_cached_data_handles_db_error(mock_get_conn: MagicMock):
    """Test that get_cached_data returns None if a database error occurs."""
    mock_get_conn.side_effect = sqlite3.Error("Simulated DB error during connection")
    cached_result = get_cached_data("any_source", {"any": "param"})
    assert cached_result is None
    # (logger.error should have been called, can be asserted with log capture if needed)

@patch("app.db.database.get_db_connection")
def test_set_cached_data_handles_db_error(mock_get_conn: MagicMock):
    """Test that set_cached_data handles database errors gracefully (e.g., doesn't crash)."""
    mock_get_conn.side_effect = sqlite3.Error("Simulated DB error during set")
    # We don't expect an exception to propagate out of set_cached_data
    try:
        set_cached_data("any_source", {"any": "param"}, {"data": "test"})
    except sqlite3.Error:
        pytest.fail("set_cached_data should not propagate raw sqlite3.Error")
    # (logger.error should have been called)

@patch("app.db.database.get_db_connection")
def test_initialize_cache_table_success(mock_get_conn: MagicMock):
    """Test that initialize_cache_table executes expected CREATE TABLE and CREATE INDEX queries."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    initialize_cache_table()

    # Check for CREATE TABLE and CREATE INDEX statements
    # This is a bit loose, just checking parts of the expected queries.
    # More specific matching could be done if necessary.
    executed_sqls = [call_args[0][0].strip() for call_args in mock_cursor.execute.call_args_list]

    assert any("CREATE TABLE IF NOT EXISTS external_data_cache" in sql for sql in executed_sqls)
    assert any("CREATE INDEX IF NOT EXISTS idx_cache_source_params_hash" in sql for sql in executed_sqls)
    assert any("CREATE INDEX IF NOT EXISTS idx_cache_expires_at" in sql for sql in executed_sqls)
    mock_conn.commit.assert_called_once()

@patch("app.db.database.get_db_connection")
def test_initialize_cache_table_handles_db_error(mock_get_conn: MagicMock):
    """Test that initialize_cache_table handles database errors gracefully."""
    mock_get_conn.side_effect = sqlite3.Error("Simulated DB error during init_cache_table")
    try:
        initialize_cache_table()
    except sqlite3.Error:
        pytest.fail("initialize_cache_table should not propagate raw sqlite3.Error")
    # (logger.error should have been called)
