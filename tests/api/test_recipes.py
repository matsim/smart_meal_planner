"""
Tests pour les endpoints /api/v1/recipes/
Couvre : création, lecture, liste, mise à jour, recalcul nutrition, import async.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FOOD_BASE = {
    "energy_kcal": 165.0, "proteins_g": 31.0, "fat_g": 3.6,
    "carbohydrates_g": 0.0, "fiber_g": 0.0, "water_g": 65.0,
}


def _create_food(client, name="Poulet"):
    resp = client.post("/api/v1/foods/", json={"name": name, **FOOD_BASE})
    assert resp.status_code == 200
    return resp.json()


def _recipe_payload(food_id, name="Poulet rôti"):
    return {
        "name": name,
        "type": "complete",
        "ingredients_food": [{"food_id": food_id, "quantity_g": 200.0}],
    }


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------

def test_create_recipe(client):
    """POST / crée la recette et calcule automatiquement IS et DE."""
    food = _create_food(client)
    resp = client.post("/api/v1/recipes/", json=_recipe_payload(food["id"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Poulet rôti"
    assert data["energy_density"] is not None
    assert data["satiety_index"] is not None
    assert len(data["ingredients"]) == 1


def test_create_recipe_without_ingredients(client):
    """Une recette sans ingrédients est créée avec IS=0 et DE=0."""
    resp = client.post("/api/v1/recipes/", json={"name": "Vide", "type": "complete"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["energy_density"] == 0.0
    assert data["satiety_index"] == 0.0


def test_create_recipe_nutrition_values(client):
    """Les valeurs nutritionnelles calculées reflètent les ingrédients."""
    # Aliment riche en eau → IS élevé
    food = client.post("/api/v1/foods/", json={
        "name": "Concombre", "energy_kcal": 15.0, "proteins_g": 0.7,
        "fat_g": 0.1, "carbohydrates_g": 3.6, "fiber_g": 0.5, "water_g": 95.0,
    }).json()

    resp = client.post("/api/v1/recipes/", json={
        "name": "Salade de concombre",
        "type": "simple",
        "ingredients_food": [{"food_id": food["id"], "quantity_g": 300.0}],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["energy_density"] > 0
    assert data["satiety_index"] > 0


def test_create_recipe_multiple_ingredients(client):
    """Une recette avec plusieurs ingrédients stocke tous les ingrédients."""
    f1 = _create_food(client, "Riz")
    f2 = _create_food(client, "Haricots")
    resp = client.post("/api/v1/recipes/", json={
        "name": "Riz haricots",
        "type": "complete",
        "ingredients_food": [
            {"food_id": f1["id"], "quantity_g": 150.0},
            {"food_id": f2["id"], "quantity_g": 100.0},
        ],
    })
    assert resp.status_code == 200
    assert len(resp.json()["ingredients"]) == 2


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

def test_read_recipe(client):
    """GET /{recipe_id} retourne la recette complète avec ses ingrédients."""
    food = _create_food(client)
    created = client.post("/api/v1/recipes/", json=_recipe_payload(food["id"])).json()
    resp = client.get(f"/api/v1/recipes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert len(resp.json()["ingredients"]) == 1


def test_read_recipe_not_found(client):
    """GET /{recipe_id} sur un ID inexistant → 404."""
    resp = client.get("/api/v1/recipes/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Liste
# ---------------------------------------------------------------------------

def test_get_all_recipes(client):
    """GET / retourne toutes les recettes."""
    food = _create_food(client)
    client.post("/api/v1/recipes/", json=_recipe_payload(food["id"], "Recette A"))
    client.post("/api/v1/recipes/", json=_recipe_payload(food["id"], "Recette B"))

    resp = client.get("/api/v1/recipes/")
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "Recette A" in names
    assert "Recette B" in names


def test_get_all_recipes_search(client):
    """GET /?search= filtre par nom de recette."""
    food = _create_food(client)
    client.post("/api/v1/recipes/", json=_recipe_payload(food["id"], "Poulet au curry"))
    client.post("/api/v1/recipes/", json=_recipe_payload(food["id"], "Sauté de légumes"))

    resp = client.get("/api/v1/recipes/?search=curry")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert "curry" in items[0]["name"].lower()


def test_get_all_recipes_empty(client):
    """GET / sur une base vide → liste vide."""
    resp = client.get("/api/v1/recipes/")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Mise à jour
# ---------------------------------------------------------------------------

def test_update_recipe_name(client):
    """PUT /{recipe_id} met à jour le nom."""
    food = _create_food(client)
    created = client.post("/api/v1/recipes/", json=_recipe_payload(food["id"])).json()
    recipe_id = created["id"]

    updated_payload = {**_recipe_payload(food["id"]), "name": "Poulet mariné"}
    resp = client.put(f"/api/v1/recipes/{recipe_id}", json=updated_payload)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Poulet mariné"


def test_update_recipe_replaces_ingredients(client):
    """PUT remplace tous les ingrédients (delete + recreate)."""
    f1 = _create_food(client, "Ancien ingrédient")
    f2 = _create_food(client, "Nouvel ingrédient")
    created = client.post("/api/v1/recipes/", json=_recipe_payload(f1["id"])).json()
    recipe_id = created["id"]

    new_payload = {
        "name": "Recette modifiée",
        "type": "complete",
        "ingredients_food": [{"food_id": f2["id"], "quantity_g": 300.0}],
    }
    resp = client.put(f"/api/v1/recipes/{recipe_id}", json=new_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["food"]["id"] == f2["id"]


def test_update_recipe_recalculates_nutrition(client):
    """PUT recalcule IS et DE après modification des ingrédients."""
    food_low_water = client.post("/api/v1/foods/", json={
        "name": "Noix", "energy_kcal": 654.0, "proteins_g": 15.0,
        "fat_g": 65.0, "carbohydrates_g": 14.0, "fiber_g": 6.5, "water_g": 4.0,
    }).json()
    food_high_water = client.post("/api/v1/foods/", json={
        "name": "Concombre", "energy_kcal": 15.0, "proteins_g": 0.7,
        "fat_g": 0.1, "carbohydrates_g": 3.6, "fiber_g": 0.5, "water_g": 95.0,
    }).json()

    created = client.post("/api/v1/recipes/", json={
        "name": "Recette initiale", "type": "complete",
        "ingredients_food": [{"food_id": food_low_water["id"], "quantity_g": 100.0}],
    }).json()
    is_before = created["satiety_index"]

    updated = client.put(f"/api/v1/recipes/{created['id']}", json={
        "name": "Recette modifiée", "type": "complete",
        "ingredients_food": [{"food_id": food_high_water["id"], "quantity_g": 300.0}],
    }).json()
    is_after = updated["satiety_index"]

    # Le concombre (eau=95%) doit produire un IS plus élevé que les noix
    assert is_after > is_before


def test_update_recipe_not_found(client):
    """PUT /{recipe_id} sur un ID inexistant → 404."""
    food = _create_food(client)
    resp = client.put("/api/v1/recipes/999999", json=_recipe_payload(food["id"]))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Import asynchrone (scraping)
# ---------------------------------------------------------------------------

def test_import_recipe_returns_202_and_task_id(client):
    """POST /import retourne 202 avec un task_id."""
    resp = client.post("/api/v1/recipes/import?url=https://www.example.com/recipe")
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "pending"


def test_get_import_status_not_found(client):
    """GET /import/status/{task_id} sur un task_id inexistant → 404."""
    resp = client.get("/api/v1/recipes/import/status/nonexistent-task-id")
    assert resp.status_code == 404


def test_get_import_status_after_creation(client):
    """GET /import/status/{task_id} retourne le statut de la tâche créée."""
    import_resp = client.post("/api/v1/recipes/import?url=https://www.example.com/recipe")
    task_id = import_resp.json()["task_id"]

    status_resp = client.get(f"/api/v1/recipes/import/status/{task_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["task_id"] == task_id
    assert data["status"] in ("pending", "completed", "failed")
