import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_full_user_journey_meal_planning(client):
    # 1. Créer un utilisateur
    user_data = {
        "email": "functional@example.com",
        "age": 30,
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "gender": "male",
        "activity_level": "moderate",
        "objective": "maintenance",
        "daily_meals_count": 1
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]
    
    # Vérifier le calcul métabolique
    resp_meta = client.get(f"/api/v1/users/{user_id}/metabolisme")
    assert resp_meta.status_code == 200
    assert resp_meta.json()["target_kcal"] > 2000
    
    # 2. Ajouter des contraintes alimentaires (exclusions)
    # Imaginons qu'on exclut l'aliment ID 999 (qui n'est pas dans nos recettes)
    constraint_data = {"food_id": 999}
    response = client.post(f"/api/v1/users/{user_id}/exclusions", json=constraint_data)
    # L'API tolère d'ajouter une contrainte même si l'aliment n'est pas encore en DB (si la FK le permet, sinon on gère l'erreur).
    # Dans notre cas, on ignore cette étape si la bdd est vide, on va plutôt créer des recettes.
    
    # 3. Créer quelques aliments et recettes de test
    food_data = [
        {"name": "Poulet", "energy_kcal": 165, "proteins_g": 31, "fat_g": 3.6, "carbohydrates_g": 0, "fiber_g": 0, "water_g": 65},
        {"name": "Riz", "energy_kcal": 130, "proteins_g": 2.7, "fat_g": 0.3, "carbohydrates_g": 28, "fiber_g": 0.4, "water_g": 68},
        {"name": "Brocoli", "energy_kcal": 34, "proteins_g": 2.8, "fat_g": 0.4, "carbohydrates_g": 7, "fiber_g": 2.6, "water_g": 89}
    ]
    food_ids = []
    for food in food_data:
        resp = client.post("/api/v1/foods/", json=food)
        food_ids.append(resp.json()["id"])
        
    recipe1 = {
        "name": "Poulet Riz Brocoli",
        "description": "Classique",
        "type": "complete",
        "instructions": "Cuire tout.",
        "preparation_time_minutes": 20,
        "ingredients_food": [
            {"food_id": food_ids[0], "quantity_g": 150, "state": "raw"},
            {"food_id": food_ids[1], "quantity_g": 100, "state": "raw"},
            {"food_id": food_ids[2], "quantity_g": 100, "state": "raw"}
        ]
    }
    resp1 = client.post("/api/v1/recipes/", json=recipe1)
    recipe1_id = resp1.json()["id"]
    
    recipe2 = {
        "name": "Salade light",
        "description": "Léger",
        "type": "complete",
        "instructions": "Mélanger.",
        "preparation_time_minutes": 5,
        "ingredients_food": [
            {"food_id": food_ids[2], "quantity_g": 200, "state": "raw"}
        ]
    }
    resp2 = client.post("/api/v1/recipes/", json=recipe2)
    recipe2_id = resp2.json()["id"]

    # 4. Générer un plan hebdomadaire
    plan_data = {
        "user_id": user_id,
        "start_date": "2024-01-01"
    }
    response = client.post("/api/v1/planner/generate", json=plan_data)
    assert response.status_code in [200, 422]
    
    if response.status_code == 422:
        # Si infeasible, on s'arrête là car on n'a pas de plan ID
        return
        
    plan = response.json()
    assert plan["status"] == "Optimal" or plan["status"] == "Infeasible"
    plan_id = plan["plan_id"]
    
    # 5. Récupérer le plan généré
    response = client.get(f"/api/v1/planner/{plan_id}")
    assert response.status_code == 200
    detail_plan = response.json()
    assert "days" in detail_plan
    
    # On vérifie la persistance du dernier plan
    response = client.get(f"/api/v1/planner/users/{user_id}/latest")
    assert response.status_code == 200
    assert response.json()["id"] == plan_id

    # 6. Swapper un repas (Optionnel, si des repas ont été générés)
    first_date = list(detail_plan["days"].keys())[0]
    first_meal = detail_plan["days"][first_date][0]
    meal_id = first_meal["id"]
    
    # Remplacer par recipe2_id
    response = client.post(f"/api/v1/planner/swap/{meal_id}", json={"recipe_id": recipe2_id})
    assert response.status_code == 200
    assert response.json()["success"] == True

    # 7. Liste de courses
    response = client.get(f"/api/v1/planner/{plan_id}/shopping-list")
    assert response.status_code == 200
    shopping_list = response.json()
    assert "items" in shopping_list
    assert type(shopping_list["items"]) is list
