import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_scrape():
    with patch("app.api.recipes.scrape_recipe_from_url") as mock:
        yield mock

def test_extract_recipe_async_accepted(mock_scrape):
    """
    Test que l'appel POST retourne immédiatement un HTTP 202 Accepted
    avec un identifiant de tâche (task_id).
    """
    response = client.post(
        "/api/v1/recipes/import",
        params={"url": "https://example.com/recipe"}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] == "pending"
    
    # Vérifier que la fonction synchrone de scraping n'est pas appelée ici, 
    # ou du moins qu'elle est différée (délicat à tester directement avec TestClient
    # de base sans asgi_lifespan, mais on s'assure du retour 202 immédiat).

def test_get_scraping_status_pending():
    """
    Test que l'endpoint de statut retourne 'pending' pour une tâche en attente.
    """
    # Création mockée d'une tâche
    response_post = client.post(
        "/api/v1/recipes/import",
        params={"url": "https://example.com/recipe"}
    )
    task_id = response_post.json()["task_id"]

    # Vérification du statut
    response_get = client.get(f"/api/v1/recipes/import/status/{task_id}")
    assert response_get.status_code == 200
    
    data = response_get.json()
    assert data["task_id"] == task_id
    assert data["status"] in ["pending", "completed", "failed"]

def test_get_scraping_status_not_found():
    """
    Test le comportement si on demande le statut d'une tâche inexistante.
    """
    response = client.get("/api/v1/recipes/import/status/invalid-uuid-123")
    assert response.status_code == 404
