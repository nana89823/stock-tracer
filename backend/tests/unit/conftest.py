"""Conftest for unit tests that use sync SQLite (not async).

Overrides the autouse setup_db fixture from the parent conftest to prevent
Base.metadata.create_all from running with the async engine, which fails
due to the Strategy model using JSONB (unsupported by SQLite).
"""

import pytest


@pytest.fixture(autouse=True)
def setup_db():
    """Override parent conftest's autouse setup_db to do nothing.

    Each unit test module manages its own table setup/teardown.
    """
    yield
