import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop so all async tests share one loop.

    The shared SQLAlchemy async engine binds to the first event loop it uses.
    Using function-scoped loops causes pool connections to become stale after
    the first test's loop is closed.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
