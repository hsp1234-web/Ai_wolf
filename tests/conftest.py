import pytest
from fastapi.testclient import TestClient
import os
import tempfile
from pathlib import Path # For type hinting and path operations

# Adjust import path if your main app instance is located differently
# This assumes your project root is the parent of 'app' directory
# and 'app.main' contains the FastAPI instance named 'app'.
try:
    from app.main import app # FastAPI application instance
    from app.core.config import settings # Application settings
    from app.db.database import get_db_connection, initialize_db # DB utility functions
except ImportError as e:
    # This might happen if the subtask CWD is not the project root,
    # or if PYTHONPATH is not set up for tests to find the 'app' module.
    # For generating the file, this is okay. For running, CWD/PYTHONPATH must be correct.
    print(f"Conftest Import Error: {e}. Ensure PYTHONPATH or CWD is set correctly for test execution.")
    app = None # Placeholder if import fails in this script context
    settings = None # Placeholder

@pytest.fixture(scope="session")
def temp_db_path_session():
    """
    Fixture to create a temporary SQLite database for the entire test session.
    It overrides the DB_FILE_PATH in settings.
    Yields the path to the temporary database file.
    Cleans up the temporary database file after the test session.
    """
    if not settings: # If settings failed to import
        pytest.skip("Settings could not be imported, cannot run tests requiring DB override.")

    # Create a temporary database file
    # Using NamedTemporaryFile and then getting its name and closing it (but not deleting yet)
    # is safer as it ensures a unique name and proper handling.
    # However, mkstemp gives more direct control over not deleting on close.
    db_fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="test_session_main_")
    os.close(db_fd) # Close the file descriptor, file remains for use

    db_path = Path(db_path_str) # Convert to Path object

    # Store original DB path and override with temp path
    original_db_path = settings.DB_FILE_PATH
    settings.DB_FILE_PATH = db_path

    print(f"INFO: Using temporary database for test session: {db_path}")

    # Initialize the temporary database with schema
    # get_db_connection will now use the overridden settings.DB_FILE_PATH
    try:
        conn = get_db_connection()
        initialize_db() # This initializes 'settings' and 'external_data_cache' tables
        conn.close()
        print(f"INFO: Temporary database initialized at {db_path}")
    except Exception as e:
        print(f"ERROR: Failed to initialize temporary database: {e}")
        os.unlink(db_path) # Clean up if init failed
        raise # Re-raise to fail the setup

    yield db_path # Provide the path to the tests that depend on this fixture

    # Teardown: remove the temporary database file and restore original path
    print(f"INFO: Tearing down temporary database: {db_path}")
    try:
        os.unlink(db_path)
    except OSError as e:
        print(f"ERROR: Could not remove temporary database file {db_path}: {e}")

    settings.DB_FILE_PATH = original_db_path # Restore original settings
    print("INFO: Original DB_FILE_PATH restored in settings.")


@pytest.fixture(scope="module") # Or "session" if client can be reused across modules without issues
def client(temp_db_path_session): # Depend on temp_db_path_session to ensure DB is set up
    """
    Pytest fixture to provide a FastAPI TestClient.
    Uses the application instance ('app') from app.main.
    The client will operate on the temporary database configured by temp_db_path_session.
    """
    if not app:
        pytest.skip("FastAPI app ('app.main.app') could not be imported, skipping client-based tests.")

    # The TestClient uses the 'app' instance. If 'app' reads settings upon its creation,
    # then the settings override (DB_FILE_PATH) must happen before 'app' is imported or created.
    # In our case, 'settings' is a global Pydantic object, and 'app' modules import it.
    # So, overriding 'settings.DB_FILE_PATH' in 'temp_db_path_session' *before* this client
    # fixture runs should be effective, as long as 'app' components (like get_db_connection)
    # reference the live 'settings.DB_FILE_PATH' rather than a cached one from import time.
    # This is typically how Pydantic settings objects work.

    with TestClient(app) as c:
        yield c

    # No specific teardown for client needed here, as TestClient handles its own lifecycle.
    # The temp_db_path_session fixture handles DB teardown.
