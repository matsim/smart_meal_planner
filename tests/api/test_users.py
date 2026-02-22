def test_create_user(client):
    user_data = {
        "email": "test@example.com",
        "age": 30,
        "weight_kg": 80.0,
        "height_cm": 180.0,
        "gender": "male",
        "activity_level": "moderate",
        "daily_meals_count": 3,
        "objective": "weight_loss",
        "preferences": {
            "is_vegetarian": False,
            "is_vegan": False,
            "is_gluten_free": False,
            "is_lactose_free": False,
            "override_protein_ratio": 0.4
        }
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["id"] is dict or data["id"] is not None
    assert data["preferences"]["override_protein_ratio"] == 0.4

def test_create_user_duplicate_email(client):
    user_data = {
        "email": "duplicate@example.com",
        "age": 30,
        "weight_kg": 80.0,
        "height_cm": 180.0,
        "gender": "male"
    }
    client.post("/api/v1/users/", json=user_data)
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 400
    assert "existe déjà" in response.json()["detail"]

def test_read_metabolic_profile(client):
    user_data = {
        "email": "metabolism@example.com",
        "age": 30,
        "weight_kg": 80.0,
        "height_cm": 180.0,
        "gender": "male",
        "activity_level": "moderate",
        "objective": "weight_loss"
    }
    resp = client.post("/api/v1/users/", json=user_data)
    user_id = resp.json()["id"]
    
    # Tester l'endpoint du profil 
    response = client.get(f"/api/v1/users/{user_id}/metabolisme")
    assert response.status_code == 200
    profile = response.json()
    
    # BMR: 1780.0, TDEE: 2759.0, Objectif Perte: TDEE - 500 = 2259.0
    assert profile["bmr"] == 1780.0
    assert profile["tdee"] == 2759.0
    assert profile["target_kcal"] == 2259.0
