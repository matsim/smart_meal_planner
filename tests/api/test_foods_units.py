import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.food import Food

def test_create_food_with_conversion_units(client: TestClient, db_session: Session):
    # Création d'un aliment avec densité spécifique (ex: Farine)
    payload = {
        "name": "Farine de blé",
        "energy_kcal": 364,
        "proteins_g": 10,
        "carbohydrates_g": 76,
        "fat_g": 1,
        "fiber_g": 3,
        "water_g": 10,
        "density": 0.6,
        "portion_weight_g": 150.0 # Poids d'une tasse
    }
    
    response = client.post("/api/v1/foods/", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Farine de blé"
    assert data["density"] == 0.6
    assert data["portion_weight_g"] == 150.0

def test_update_food_conversion_units(client: TestClient, db_session: Session):
    # Setup : Aliment classique
    food = Food(name="Huile d'olive", energy_kcal=900, fat_g=100)
    db_session.add(food)
    db_session.commit()
    
    # Mise à jour de l'aliment pour préciser sa densité
    payload = {
        "name": "Huile d'olive Extra",
        "energy_kcal": 900,
        "proteins_g": 0,
        "carbohydrates_g": 0,
        "fat_g": 100,
        "fiber_g": 0,
        "water_g": 0,
        "density": 0.9, # L'huile est moins dense que l'eau
        "portion_weight_g": 15.0 # Une cuillère à soupe
    }
    
    response = client.put(f"/api/v1/foods/{food.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Huile d'olive Extra"
    assert data["density"] == 0.9
    assert data["portion_weight_g"] == 15.0

def test_create_food_default_conversions(client: TestClient, db_session: Session):
    # Vérifier que les valeurs par défaut s'appliquent si non fournies
    payload = {
        "name": "Eau potable",
        "energy_kcal": 0,
        "proteins_g": 0,
        "carbohydrates_g": 0,
        "fat_g": 0,
        "fiber_g": 0,
        "water_g": 100
    }
    
    response = client.post("/api/v1/foods/", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["density"] == 1.0
    assert data["portion_weight_g"] == 100.0
