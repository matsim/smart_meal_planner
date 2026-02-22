import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_user_journey_meal_planning():
    # 1. Créer un utilisateur
    user_data = {
        "age": 30,
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "gender": "male",
        "activity_level": "moderate",
        "goal": "maintenance"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]
    
    # Vérifier le calcul métabolique
    assert user["target_kcal"] > 2000
    
    # 2. Ajouter des contraintes alimentaires (exclusions)
    # Imaginons qu'on exclut l'aliment ID 1 (qui pourrait être un test)
    constraint_data = {"food_id": 1}
    response = client.post(f"/users/{user_id}/constraints", json=constraint_data)
    # L'API tolère d'ajouter une contrainte même si l'aliment n'est pas encore en DB (si la FK le permet, sinon on gère l'erreur).
    # Dans notre cas, on ignore cette étape si la bdd est vide, on va plutôt créer des recettes.
    
    # 3. Créer quelques aliments et recettes de test
    food_data = [
        {"name": "Poulet", "calories_per_100g": 165, "protein_per_100g": 31, "fat_per_100g": 3.6, "carbs_per_100g": 0},
        {"name": "Riz", "calories_per_100g": 130, "protein_per_100g": 2.7, "fat_per_100g": 0.3, "carbs_per_100g": 28},
        {"name": "Brocoli", "calories_per_100g": 34, "protein_per_100g": 2.8, "fat_per_100g": 0.4, "carbs_per_100g": 7}
    ]
    food_ids = []
    for food in food_data:
        resp = client.post("/foods/", json=food)
        food_ids.append(resp.json()["id"])
        
    recipe1 = {
        "name": "Poulet Riz Brocoli",
        "description": "Classique",
        "type": "lunch",
        "instructions": "Cuire tout.",
        "preparation_time_minutes": 20,
        "ingredients": [
            {"food_id": food_ids[0], "quantity_g": 150},
            {"food_id": food_ids[1], "quantity_g": 100},
            {"food_id": food_ids[2], "quantity_g": 100}
        ]
    }
    resp1 = client.post("/recipes/", json=recipe1)
    recipe1_id = resp1.json()["id"]
    
    recipe2 = {
        "name": "Salade light",
        "description": "Léger",
        "type": "dinner",
        "instructions": "Mélanger.",
        "preparation_time_minutes": 5,
        "ingredients": [
            {"food_id": food_ids[2], "quantity_g": 200}
        ]
    }
    resp2 = client.post("/recipes/", json=recipe2)
    recipe2_id = resp2.json()["id"]

    # 4. Générer un plan hebdomadaire
    plan_data = {
        "user_id": user_id,
        "start_date": "2024-01-01"
    }
    response = client.post("/planner/generate", json=plan_data)
    assert response.status_code == 200
    plan = response.json()
    assert plan["status"] == "Optimal" or plan["status"] == "Infeasible"
    plan_id = plan["plan_id"]
    
    # 5. Récupérer le plan généré
    response = client.get(f"/planner/{plan_id}")
    assert response.status_code == 200
    detail_plan = response.json()
    assert "days" in detail_plan
    
    # On vérifie la persistance du dernier plan
    response = client.get(f"/planner/users/{user_id}/latest")
    assert response.status_code == 200
    assert response.json()["id"] == plan_id

    # 6. Swapper un repas (Optionnel, si des repas ont été générés)
    first_date = list(detail_plan["days"].keys())[0]
    first_meal = detail_plan["days"][first_date][0]
    meal_id = first_meal["id"]
    
    # Remplacer par recipe2_id
    response = client.put(f"/planner/meals/{meal_id}", json={"recipe_id": recipe2_id})
    assert response.status_code == 200
    assert response.json()["success"] == True

    # 7. Liste de courses
    response = client.get(f"/planner/{plan_id}/shopping-list")
    assert response.status_code == 200
    shopping_list = response.json()
    assert "items" in shopping_list
    assert type(shopping_list["items"]) is list
