from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_todos_for_empty(client):
    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert response['message'] == "fetched all todos successfully"
    assert response.todos == []
     