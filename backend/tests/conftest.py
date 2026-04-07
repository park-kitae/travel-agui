"""
공용 pytest fixture
"""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
async def client():
    """FastAPI 앱을 실제 서버 없이 직접 호출하는 비동기 클라이언트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
