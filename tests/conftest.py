"""pytest configuration and shared fixtures."""
import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for tests."""
    return tmp_path
