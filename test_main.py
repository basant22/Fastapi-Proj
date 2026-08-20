import pytest
from fastapi.testclient import TestClient
from main import app


# 1. Use a pytest fixture for clean client handling
@pytest.fixture
def client():
    return TestClient(app)


def test_get_todos_for_empty(client):
    response = client.get("/todos")
    assert response.status_code == 200

    # Parse JSON body
    data = response.json()

    # 2. Access values from `data`, NOT directly from `response`
    assert data["message"] == "fetched all todos successfully"
    assert data["todos"] == []
     