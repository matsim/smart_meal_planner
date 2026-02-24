BASE_USER = {
    "email": "base@example.com",
    "age": 30,
    "weight_kg": 80.0,
    "height_cm": 180.0,
    "gender": "male",
    "activity_level": "sedentary",
    "daily_meals_count": 3,
    "objective": "weight_loss",
}


def _create_user(client, overrides=None):
    data = {**BASE_USER, **(overrides or {})}
    resp = client.post("/api/v1/users/", json=data)
    assert resp.status_code == 200
    return resp.json()


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


# --- Nouveaux tests ---

def test_read_user(client):
    """GET /{user_id} retourne l'utilisateur existant."""
    user = _create_user(client, {"email": "read@example.com"})
    resp = client.get(f"/api/v1/users/{user['id']}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "read@example.com"


def test_read_user_not_found(client):
    """GET /{user_id} sur un ID inexistant → 404."""
    resp = client.get("/api/v1/users/999999")
    assert resp.status_code == 404


def test_read_metabolic_profile_not_found(client):
    """GET metabolisme pour un utilisateur inexistant → 404."""
    resp = client.get("/api/v1/users/999999/metabolisme")
    assert resp.status_code == 404


def test_read_metabolic_profile_incomplete_data(client):
    """GET metabolisme sans données physiologiques → 400."""
    user = _create_user(client, {
        "email": "incomplete@example.com",
        "age": None, "weight_kg": None, "height_cm": None, "gender": None,
    })
    resp = client.get(f"/api/v1/users/{user['id']}/metabolisme")
    assert resp.status_code == 400
    assert "incomplètes" in resp.json()["detail"]


def test_read_metabolic_profile_all_objectives(client):
    """Les trois objectifs calculent des cibles différentes pour le même profil."""
    profiles = {}
    for obj in ("weight_loss", "maintenance", "muscle_gain"):
        user = _create_user(client, {"email": f"{obj}@example.com", "objective": obj})
        resp = client.get(f"/api/v1/users/{user['id']}/metabolisme")
        assert resp.status_code == 200
        profiles[obj] = resp.json()["target_kcal"]

    # weight_loss < maintenance < muscle_gain
    assert profiles["weight_loss"] < profiles["maintenance"] < profiles["muscle_gain"]


def test_update_metabolic_profile(client):
    """PUT metabolisme met à jour le poids et recalcule le profil."""
    user = _create_user(client, {"email": "update@example.com"})
    user_id = user["id"]

    before = client.get(f"/api/v1/users/{user_id}/metabolisme").json()

    # Augmenter le poids → BMR plus élevé
    resp = client.put(f"/api/v1/users/{user_id}/metabolisme", json={"weight_kg": 100.0})
    assert resp.status_code == 200
    after = resp.json()
    assert after["bmr"] > before["bmr"]


def test_update_metabolic_profile_not_found(client):
    """PUT metabolisme pour un utilisateur inexistant → 404."""
    resp = client.put("/api/v1/users/999999/metabolisme", json={"weight_kg": 90.0})
    assert resp.status_code == 404


def test_read_user_constraints_empty(client):
    """GET exclusions d'un utilisateur sans contraintes → liste vide."""
    user = _create_user(client, {"email": "noconstraints@example.com"})
    resp = client.get(f"/api/v1/users/{user['id']}/exclusions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_and_read_user_constraint(client):
    """POST exclusion ajoute une contrainte, GET la retourne."""
    user = _create_user(client, {"email": "constraint@example.com"})
    user_id = user["id"]

    # Créer un aliment à exclure
    food_resp = client.post("/api/v1/foods/", json={
        "name": "Arachides", "energy_kcal": 580.0, "proteins_g": 26.0,
        "fat_g": 49.0, "carbohydrates_g": 16.0, "fiber_g": 8.0, "water_g": 5.0,
    })
    food_id = food_resp.json()["id"]

    resp = client.post(f"/api/v1/users/{user_id}/exclusions", json={"food_id": food_id})
    assert resp.status_code == 200
    assert resp.json()["food_id"] == food_id

    constraints = client.get(f"/api/v1/users/{user_id}/exclusions").json()
    assert len(constraints) == 1
    assert constraints[0]["food_id"] == food_id


def test_add_user_constraint_duplicate_is_idempotent(client):
    """Ajouter la même exclusion deux fois retourne la contrainte existante sans doublon."""
    user = _create_user(client, {"email": "dup_constraint@example.com"})
    user_id = user["id"]

    food_resp = client.post("/api/v1/foods/", json={
        "name": "Lait", "energy_kcal": 62.0, "proteins_g": 3.2,
        "fat_g": 3.5, "carbohydrates_g": 4.8, "fiber_g": 0.0, "water_g": 88.0,
    })
    food_id = food_resp.json()["id"]

    client.post(f"/api/v1/users/{user_id}/exclusions", json={"food_id": food_id})
    client.post(f"/api/v1/users/{user_id}/exclusions", json={"food_id": food_id})

    constraints = client.get(f"/api/v1/users/{user_id}/exclusions").json()
    assert len(constraints) == 1  # pas de doublon


def test_remove_user_constraint(client):
    """DELETE exclusion la retire correctement."""
    user = _create_user(client, {"email": "remove_constraint@example.com"})
    user_id = user["id"]

    food_resp = client.post("/api/v1/foods/", json={
        "name": "Blé", "energy_kcal": 340.0, "proteins_g": 13.0,
        "fat_g": 2.5, "carbohydrates_g": 70.0, "fiber_g": 10.0, "water_g": 12.0,
    })
    food_id = food_resp.json()["id"]

    client.post(f"/api/v1/users/{user_id}/exclusions", json={"food_id": food_id})
    del_resp = client.delete(f"/api/v1/users/{user_id}/exclusions/{food_id}")
    assert del_resp.status_code == 200

    constraints = client.get(f"/api/v1/users/{user_id}/exclusions").json()
    assert constraints == []


def test_remove_user_constraint_not_found(client):
    """DELETE exclusion inexistante → 404."""
    user = _create_user(client, {"email": "noconstraint@example.com"})
    resp = client.delete(f"/api/v1/users/{user['id']}/exclusions/999999")
    assert resp.status_code == 404
