"""
Tests pour les endpoints /api/v1/planner/
Couvre : génération de plan, récupération, liste de courses, alternatives, swap.
"""
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FOOD_BASE = {
    "energy_kcal": 165.0, "proteins_g": 31.0, "fat_g": 3.6,
    "carbohydrates_g": 0.0, "fiber_g": 0.0, "water_g": 65.0,
}

# Profil utilisateur qui génère une cible calorique atteignable par le solveur
# BMR = 10*80 + 6.25*180 - 5*30 + 5 = 1780
# TDEE = 1780 * 1.2 = 2136   (sédentaire)
# WEIGHT_LOSS = 2136 - 500 = 1636   (safety floor: 1780*0.9=1602 → ok)
# Avec 3 repas/jour et les candidats à ~400-850 kcal (avg 625), cible 1636/3 ≈ 545 kcal/repas
# Test utilise tolerance=0.30 pour robustesse

BASE_USER = {
    "email": "planner@test.com",
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


def _create_food(client, name="Aliment test"):
    resp = client.post("/api/v1/foods/", json={"name": name, **FOOD_BASE})
    assert resp.status_code == 200
    return resp.json()


def _create_recipe(client, food_id, name="Recette test"):
    resp = client.post("/api/v1/recipes/", json={
        "name": name,
        "type": "complete",
        "ingredients_food": [{"food_id": food_id, "quantity_g": 200.0}],
    })
    assert resp.status_code == 200
    return resp.json()


def _setup_user_and_recipes(client, n=10, email="setup@test.com"):
    """Crée un utilisateur + n recettes (avec un aliment commun)."""
    user = _create_user(client, {"email": email})
    food = _create_food(client, "Ingrédient commun")
    recipes = [_create_recipe(client, food["id"], f"Recette {i}") for i in range(n)]
    return user, recipes


# ---------------------------------------------------------------------------
# Génération de plan
# ---------------------------------------------------------------------------

def test_generate_plan_success(client):
    """POST /generate crée un plan et retourne plan_id + kcal atteintes."""
    user, _ = _setup_user_and_recipes(client, n=10, email="gen_ok@test.com")

    resp = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"],
        "start_date": "2025-01-06",
        "tolerance": 0.30,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "plan_id" in data
    assert data["achieved_kcal_weekly"] > 0


def test_generate_plan_user_not_found(client):
    """POST /generate avec user_id inexistant → 404."""
    resp = client.post("/api/v1/planner/generate", json={
        "user_id": 999999,
        "start_date": "2025-01-06",
    })
    assert resp.status_code == 404


def test_generate_plan_no_recipes(client):
    """POST /generate sans recettes en base → 400 (pas assez de recettes)."""
    user = _create_user(client, {"email": "norecipes@test.com"})
    resp = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"],
        "start_date": "2025-01-06",
    })
    assert resp.status_code == 400


def test_generate_plan_too_few_recipes(client):
    """POST /generate avec moins de daily_meals_count*2 recettes → 400."""
    user = _create_user(client, {"email": "fewrecipes@test.com", "daily_meals_count": 3})
    food = _create_food(client, "Aliment peu")
    # Créer seulement 5 recettes, alors qu'il en faut >= 3*2=6
    for i in range(5):
        _create_recipe(client, food["id"], f"Trop peu {i}")

    resp = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"],
        "start_date": "2025-01-06",
    })
    assert resp.status_code == 400


def test_generate_plan_incomplete_metabolic_profile(client):
    """POST /generate avec profil incomplet (pas de données physio) → 400."""
    user = _create_user(client, {
        "email": "nophysio@test.com",
        "age": None, "weight_kg": None, "height_cm": None, "gender": None,
    })
    resp = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"],
        "start_date": "2025-01-06",
    })
    assert resp.status_code == 400


def test_generate_plan_with_constraint_filters_recipe(client):
    """Les recettes contenant un aliment exclu sont retirées du plan."""
    user = _create_user(client, {"email": "constrained@test.com", "daily_meals_count": 3})
    food_ok = _create_food(client, "Aliment autorisé")
    food_excluded = _create_food(client, "Aliment exclu")

    # 9 recettes OK + 1 recette avec aliment exclu
    for i in range(9):
        _create_recipe(client, food_ok["id"], f"OK recette {i}")
    _create_recipe(client, food_excluded["id"], "Recette exclue")

    # Ajouter l'exclusion
    client.post(f"/api/v1/users/{user['id']}/exclusions",
                json={"food_id": food_excluded["id"]})

    resp = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"],
        "start_date": "2025-01-06",
        "tolerance": 0.30,
    })
    # Doit réussir car 9 recettes valides ≥ 3*2=6
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Récupération de plan
# ---------------------------------------------------------------------------

def test_get_plan_by_id(client):
    """GET /{plan_id} retourne le plan structuré par jours."""
    user, _ = _setup_user_and_recipes(client, n=10, email="getplan@test.com")
    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()
    plan_id = gen["plan_id"]

    resp = client.get(f"/api/v1/planner/{plan_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == plan_id
    assert "days" in data
    assert len(data["days"]) == 7


def test_get_plan_not_found(client):
    """GET /{plan_id} sur un ID inexistant → 404."""
    resp = client.get("/api/v1/planner/999999")
    assert resp.status_code == 404


def test_get_latest_plan(client):
    """GET /users/{user_id}/latest retourne le dernier plan généré."""
    user, _ = _setup_user_and_recipes(client, n=10, email="latest@test.com")

    client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    })
    resp = client.get(f"/api/v1/planner/users/{user['id']}/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "days" in data


def test_get_latest_plan_not_found(client):
    """GET /users/{user_id}/latest pour un user sans plan → 404."""
    user = _create_user(client, {"email": "noplan@test.com"})
    resp = client.get(f"/api/v1/planner/users/{user['id']}/latest")
    assert resp.status_code == 404


def test_get_plan_structure(client):
    """Le plan retourné contient les champs attendus (target_kcal, achieved_kcal, dates)."""
    user, _ = _setup_user_and_recipes(client, n=10, email="structure@test.com")
    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()

    plan = client.get(f"/api/v1/planner/{gen['plan_id']}").json()
    assert plan["target_kcal"] > 0
    assert plan["achieved_kcal"] > 0
    assert plan["start_date"] == "2025-01-06"
    assert plan["end_date"] == "2025-01-12"


# ---------------------------------------------------------------------------
# Liste de courses
# ---------------------------------------------------------------------------

def test_get_shopping_list(client):
    """GET /{plan_id}/shopping-list retourne les ingrédients agrégés."""
    user, _ = _setup_user_and_recipes(client, n=10, email="shop@test.com")
    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()
    plan_id = gen["plan_id"]

    resp = client.get(f"/api/v1/planner/{plan_id}/shopping-list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_id"] == plan_id
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    # Chaque item a food_id, food_name, total_quantity_g
    for item in data["items"]:
        assert "food_id" in item
        assert "food_name" in item
        assert item["total_quantity_g"] > 0


def test_get_shopping_list_family_multiplier(client):
    """Le multiplicateur famille double les quantités."""
    user, _ = _setup_user_and_recipes(client, n=10, email="family@test.com")
    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()
    plan_id = gen["plan_id"]

    single = client.get(f"/api/v1/planner/{plan_id}/shopping-list?family_multiplier=1").json()
    double = client.get(f"/api/v1/planner/{plan_id}/shopping-list?family_multiplier=2").json()

    # Toutes les quantités doublent
    single_map = {item["food_id"]: item["total_quantity_g"] for item in single["items"]}
    for item in double["items"]:
        assert item["total_quantity_g"] == pytest.approx(single_map[item["food_id"]] * 2, rel=0.01)


def test_get_shopping_list_plan_not_found(client):
    """GET shopping-list sur plan inexistant → 404."""
    resp = client.get("/api/v1/planner/999999/shopping-list")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Alternatives de repas
# ---------------------------------------------------------------------------

def test_get_meal_alternatives(client):
    """GET /meals/{meal_id}/alternatives retourne jusqu'à 5 alternatives."""
    user, _ = _setup_user_and_recipes(client, n=10, email="alt@test.com")
    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()

    plan = client.get(f"/api/v1/planner/{gen['plan_id']}").json()
    # Récupérer le premier repas d'un jour quelconque
    first_day = list(plan["days"].values())[0]
    meal_id = first_day[0]["id"]

    resp = client.get(f"/api/v1/planner/meals/{meal_id}/alternatives")
    assert resp.status_code == 200
    alternatives = resp.json()
    assert isinstance(alternatives, list)
    assert len(alternatives) <= 5
    for alt in alternatives:
        assert "recipe_id" in alt
        assert "recipe_name" in alt
        assert "match_score" in alt


def test_get_meal_alternatives_not_found(client):
    """GET /meals/{meal_id}/alternatives sur un repas inexistant → 404."""
    resp = client.get("/api/v1/planner/meals/999999/alternatives")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Swap de repas
# ---------------------------------------------------------------------------

def test_swap_meal(client):
    """POST /swap/{repas_id} remplace la recette d'un repas."""
    food = _create_food(client, "Aliment swap")
    user, recipes = _setup_user_and_recipes(client, n=10, email="swap@test.com")

    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()

    plan = client.get(f"/api/v1/planner/{gen['plan_id']}").json()
    first_day = list(plan["days"].values())[0]
    meal_id = first_day[0]["id"]
    old_recipe_id = first_day[0]["recipe"]["id"]

    # Créer une recette de remplacement différente
    new_recipe = _create_recipe(client, food["id"], "Nouvelle recette swap")
    new_recipe_id = new_recipe["id"]

    resp = client.post(f"/api/v1/planner/swap/{meal_id}", json={"recipe_id": new_recipe_id})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Vérifier que le repas utilise maintenant la nouvelle recette
    updated_plan = client.get(f"/api/v1/planner/{gen['plan_id']}").json()
    all_meals = [m for day in updated_plan["days"].values() for m in day]
    meal_after = next(m for m in all_meals if m["id"] == meal_id)
    assert meal_after["recipe"]["id"] == new_recipe_id


def test_swap_meal_not_found(client):
    """POST /swap/{repas_id} sur un repas inexistant → 404."""
    food = _create_food(client, "Aliment erreur")
    recipe = _create_recipe(client, food["id"], "Recette valide")
    resp = client.post("/api/v1/planner/swap/999999", json={"recipe_id": recipe["id"]})
    assert resp.status_code == 404


def test_swap_meal_recipe_not_found(client):
    """POST /swap/{repas_id} avec recipe_id inexistant → 404."""
    user, _ = _setup_user_and_recipes(client, n=10, email="swapfail@test.com")
    gen = client.post("/api/v1/planner/generate", json={
        "user_id": user["id"], "start_date": "2025-01-06", "tolerance": 0.30,
    }).json()

    plan = client.get(f"/api/v1/planner/{gen['plan_id']}").json()
    first_day = list(plan["days"].values())[0]
    meal_id = first_day[0]["id"]

    resp = client.post(f"/api/v1/planner/swap/{meal_id}", json={"recipe_id": 999999})
    assert resp.status_code == 404
