"""Placeholder test to ensure test suite runs successfully."""
from knowledge_hub import __version__


def test_version():
    """Verify package version is defined."""
    assert __version__ == "0.1.0"


def test_import():
    """Verify core package can be imported."""
    import knowledge_hub
    assert knowledge_hub.__version__ == "0.1.0"
