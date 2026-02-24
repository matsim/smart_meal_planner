"""
Tests pour les endpoints /api/v1/foods/
Couvre : list, search, read, update, delete, batch-delete, merge.
"""
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FOOD_PAYLOAD = {
    "name": "Poulet cuit",
    "energy_kcal": 165.0,
    "proteins_g": 31.0,
    "fat_g": 3.6,
    "carbohydrates_g": 0.0,
    "fiber_g": 0.0,
    "water_g": 65.0,
}


def _create_food(client, overrides=None):
    data = {**FOOD_PAYLOAD, **(overrides or {})}
    resp = client.post("/api/v1/foods/", json=data)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------

def test_create_food_non_draft(client):
    """Créer un aliment non-brouillon renvoie ses données correctement."""
    resp = client.post("/api/v1/foods/", json=FOOD_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Poulet cuit"
    assert data["energy_kcal"] == 165.0
    assert data["is_draft"] is False
    assert "id" in data


def test_create_food_draft_calls_off(client):
    """Un aliment brouillon déclenche un appel OpenFoodFacts (résultat mocké)."""
    mock_nutrition = {
        "energy_kcal": 250.0, "proteins_g": 10.0,
        "fat_g": 12.0, "carbohydrates_g": 30.0, "fiber_g": 3.0,
    }
    with patch("app.services.openfoodfacts.search_food_off", return_value=mock_nutrition):
        resp = client.post("/api/v1/foods/", json={**FOOD_PAYLOAD, "name": "Yaourt", "is_draft": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["energy_kcal"] == 250.0
    assert data["is_draft"] is True


def test_create_food_draft_off_no_result(client):
    """Si OFF ne renvoie rien, l'aliment brouillon est créé avec les données fournies."""
    with patch("app.services.openfoodfacts.search_food_off", return_value=None):
        resp = client.post("/api/v1/foods/", json={**FOOD_PAYLOAD, "name": "Inconnu", "is_draft": True})
    assert resp.status_code == 200
    assert resp.json()["energy_kcal"] == FOOD_PAYLOAD["energy_kcal"]


# ---------------------------------------------------------------------------
# Lecture / listage
# ---------------------------------------------------------------------------

def test_read_food(client):
    """GET /{food_id} retourne l'aliment."""
    food = _create_food(client)
    resp = client.get(f"/api/v1/foods/{food['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == food["id"]


def test_read_food_not_found(client):
    """GET /{food_id} sur un ID inexistant → 404."""
    resp = client.get("/api/v1/foods/999999")
    assert resp.status_code == 404


def test_list_foods(client):
    """GET / liste les aliments avec X-Total-Count dans le header."""
    _create_food(client, {"name": "Riz"})
    _create_food(client, {"name": "Pâtes"})
    resp = client.get("/api/v1/foods/")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2
    assert "X-Total-Count" in resp.headers
    assert int(resp.headers["X-Total-Count"]) >= 2


def test_list_foods_search_filter(client):
    """GET /?search= filtre par nom."""
    _create_food(client, {"name": "Saumon fumé"})
    _create_food(client, {"name": "Thon en boîte"})
    resp = client.get("/api/v1/foods/?search=saumon")
    assert resp.status_code == 200
    items = resp.json()
    assert all("saumon" in item["name"].lower() for item in items)


def test_list_foods_is_draft_filter(client):
    """GET /?is_draft=true retourne uniquement les brouillons."""
    with patch("app.services.openfoodfacts.search_food_off", return_value=None):
        _create_food(client, {"name": "Brouillon X", "is_draft": True})
    _create_food(client, {"name": "Validé Y", "is_draft": False})

    resp = client.get("/api/v1/foods/?is_draft=true")
    assert resp.status_code == 200
    drafts = resp.json()
    assert all(item["is_draft"] is True for item in drafts)
    names = [item["name"] for item in drafts]
    assert "Brouillon X" in names


def test_list_foods_pagination(client):
    """skip/limit limitent le nombre de résultats."""
    for i in range(5):
        _create_food(client, {"name": f"Aliment {i}"})
    resp = client.get("/api/v1/foods/?skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_search_foods_endpoint(client):
    """GET /search?q= retourne les aliments correspondants."""
    _create_food(client, {"name": "Huile d'olive"})
    _create_food(client, {"name": "Huile de tournesol"})
    _create_food(client, {"name": "Beurre"})
    resp = client.get("/api/v1/foods/search?q=huile")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all("huile" in item["name"].lower() for item in items)


def test_search_foods_multi_word(client):
    """Recherche multi-mots : chaque token doit être présent dans le nom."""
    _create_food(client, {"name": "Huile de tournesol"})
    _create_food(client, {"name": "Huile d'olive"})
    resp = client.get("/api/v1/foods/search?q=huile+tournesol")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert "tournesol" in items[0]["name"].lower()


def test_search_foods_no_result(client):
    """Recherche sans résultat → liste vide."""
    resp = client.get("/api/v1/foods/search?q=xyzinexistant")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Mise à jour
# ---------------------------------------------------------------------------

def test_update_food(client):
    """PUT /{food_id} met à jour les champs et passe is_draft à False."""
    food = _create_food(client, {"name": "Carotte brouillon", "is_draft": True})
    food_id = food["id"]

    updated = {**FOOD_PAYLOAD, "name": "Carotte validée", "energy_kcal": 41.0}
    resp = client.put(f"/api/v1/foods/{food_id}", json=updated)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Carotte validée"
    assert data["energy_kcal"] == 41.0
    assert data["is_draft"] is False


def test_update_food_not_found(client):
    """PUT sur un ID inexistant → 404."""
    resp = client.put("/api/v1/foods/999999", json=FOOD_PAYLOAD)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Suppression unitaire
# ---------------------------------------------------------------------------

def test_delete_food(client):
    """DELETE /{food_id} supprime l'aliment."""
    food = _create_food(client, {"name": "À supprimer"})
    food_id = food["id"]

    del_resp = client.delete(f"/api/v1/foods/{food_id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/v1/foods/{food_id}")
    assert get_resp.status_code == 404


def test_delete_food_not_found(client):
    """DELETE sur un ID inexistant → 404."""
    resp = client.delete("/api/v1/foods/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Suppression en lot
# ---------------------------------------------------------------------------

def test_batch_delete_foods(client):
    """POST /batch-delete supprime plusieurs aliments d'un coup."""
    f1 = _create_food(client, {"name": "Batch A"})
    f2 = _create_food(client, {"name": "Batch B"})
    ids = [f1["id"], f2["id"]]

    resp = client.post("/api/v1/foods/batch-delete", json=ids)
    assert resp.status_code == 200
    assert "2" in resp.json()["message"]

    # Les deux sont supprimés
    for fid in ids:
        assert client.get(f"/api/v1/foods/{fid}").status_code == 404


def test_batch_delete_foods_not_found(client):
    """POST /batch-delete avec des IDs inexistants → 404."""
    resp = client.post("/api/v1/foods/batch-delete", json=[888888, 999999])
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Fusion (merge)
# ---------------------------------------------------------------------------

def test_merge_foods_reassigns_recipe_ingredients(client):
    """POST /merge transfère les ingrédients de recettes vers la cible."""
    target = _create_food(client, {"name": "Poulet officiel"})
    source = _create_food(client, {"name": "Poulet brouillon", "is_draft": True})

    # Créer une recette utilisant la source
    recipe_resp = client.post("/api/v1/recipes/", json={
        "name": "Recette test merge",
        "type": "complete",
        "ingredients_food": [{"food_id": source["id"], "quantity_g": 200.0}],
    })
    assert recipe_resp.status_code == 200

    merge_resp = client.post("/api/v1/foods/merge", json={
        "target_id": target["id"],
        "source_ids": [source["id"]],
    })
    assert merge_resp.status_code == 200

    # La source a été supprimée
    assert client.get(f"/api/v1/foods/{source['id']}").status_code == 404

    # La recette utilise maintenant la cible
    recipe = client.get(f"/api/v1/recipes/{recipe_resp.json()['id']}").json()
    ingredient_food_ids = [ing["food"]["id"] for ing in recipe["ingredients"] if ing.get("food")]
    assert target["id"] in ingredient_food_ids


def test_merge_foods_invalid_target(client):
    """Cible inexistante → 404."""
    source = _create_food(client, {"name": "Source orpheline"})
    resp = client.post("/api/v1/foods/merge", json={
        "target_id": 999999,
        "source_ids": [source["id"]],
    })
    assert resp.status_code == 404


def test_merge_foods_empty_sources(client):
    """Liste de sources vide → 400."""
    target = _create_food(client, {"name": "Cible seule"})
    resp = client.post("/api/v1/foods/merge", json={
        "target_id": target["id"],
        "source_ids": [],
    })
    assert resp.status_code == 400
