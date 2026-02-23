import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch
from app.schemas.food import FoodCreate

def test_create_draft_triggers_off(client: TestClient, db_session: Session):
    """
    Si l'on crée un ingrédient brouillon, le script doit contacter l'API OFF
    en arrière-plan pour peupler les macros (kcal, prot, fat, carb, fib) 
    qui ont probablement été transmises en tant que (0,0,0,0).
    """
    mock_off_data = {
        "energy_kcal": 150.0,
        "proteins_g": 5.0,
        "fat_g": 8.0,
        "carbohydrates_g": 10.0,
        "fiber_g": 2.0
    }
    
    with patch('app.services.openfoodfacts.search_food_off', return_value=mock_off_data) as mock_search:
        payload = {
            "name": "Lait d'Avoine Inconnu",
            "energy_kcal": 0,
            "proteins_g": 0,
            "fat_g": 0,
            "carbohydrates_g": 0,
            "fiber_g": 0,
            "water_g": 0,
            "is_draft": True
        }
        res = client.post("/api/v1/foods/", json=payload)
        
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Lait d'Avoine Inconnu"
        assert data["energy_kcal"] == 150.0  # Prérempli par le Mock OFF
        assert data["proteins_g"] == 5.0
        assert data["is_draft"] == True      # Il reste tout de même en brouillon !
        
        mock_search.assert_called_once_with("Lait d'Avoine Inconnu")

def test_create_valid_ignores_off(client: TestClient, db_session: Session):
    """
    Si l'utilisateur (ou le seeder) crée un ingrédient validé manuellement, 
    l'API OFF ne doit pas être sollicitée pour économiser du temps réseau.
    """
    with patch('app.services.openfoodfacts.search_food_off') as mock_search:
        payload = {
            "name": "Pomme Standard",
            "energy_kcal": 52,
            "proteins_g": 0.3,
            "fat_g": 0.2,
            "carbohydrates_g": 14,
            "fiber_g": 2.4,
            "water_g": 86,
            "is_draft": False
        }
        res = client.post("/api/v1/foods/", json=payload)
        
        assert res.status_code == 200
        mock_search.assert_not_called()
