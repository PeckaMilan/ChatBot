"""Health endpoint tests."""


def test_health_endpoint(client):
    """Test health check returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_endpoint(client):
    """Test root endpoint returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ChatBot Platform"
    assert "version" in data
