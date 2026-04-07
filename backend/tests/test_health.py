"""
/health 엔드포인트 테스트
"""


async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "a2a-client"
    assert "a2a_server" in data
