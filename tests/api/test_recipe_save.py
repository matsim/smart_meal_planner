"""
Tests fonctionnels pour la sauvegarde d'une recette importée.

Couvre :
  Issue 1 — Erreur générique à l'enregistrement :
    - quantity_g optionnel : calculé depuis raw_quantity + raw_unit (g, kg, c.à.s, c.à.c)
    - quantity_g absent et raw_quantity absent → 100 g par défaut
    - food_id inexistant → 422 avec message descriptif (pas de 500 générique)
    - quantity_g explicite utilisé tel quel

  Issue 2 — Liaison automatique d'ingrédients :
    POST /api/v1/foods/match-ingredients
    - BD vide → best_match null
    - Match exact → score 1.0
    - Match partiel → résultats pertinents
    - Conversion de quantité avec l'unité
    - Plusieurs ingrédients simultanément
    - Champ quantity_g null si unité inconvertible
"""
import pytest

_FOOD_BASE = {
    "energy_kcal": 150.0,
    "proteins_g": 10.0,
    "fat_g": 5.0,
    "carbohydrates_g": 15.0,
    "fiber_g": 2.0,
    "water_g": 50.0,
}


def _food(client, name="Aliment test", **kwargs):
    r = client.post("/api/v1/foods/", json={"name": name, **_FOOD_BASE, **kwargs})
    assert r.status_code == 200, r.text
    return r.json()


# ===========================================================================
# Issue 1 — Sauvegarde robuste (quantity_g optionnel)
# ===========================================================================

class TestRecipeSaveQuantity:
    def test_explicit_quantity_g_used_directly(self, client):
        """quantity_g fourni → valeur conservée exactement."""
        food = _food(client, "Riz basmati")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Riz au curry",
            "type": "complete",
            "ingredients_food": [
                {"food_id": food["id"], "quantity_g": 300.0},
            ],
        })
        assert resp.status_code == 200
        ing = resp.json()["ingredients"][0]
        assert ing["quantity_g"] == 300.0

    def test_raw_unit_g_converts_to_quantity_g(self, client):
        """raw_unit='g' + raw_quantity=200 → quantity_g=200."""
        food = _food(client, "Farine")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Pate a crepes",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 200.0, "raw_unit": "g"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 200.0

    def test_raw_unit_kg_converts_to_grams(self, client):
        """raw_unit='kg' + raw_quantity=0.5 → quantity_g=500."""
        food = _food(client, "Boeuf")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Boeuf braise",
            "type": "complete",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 0.5, "raw_unit": "kg"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 500.0

    def test_raw_unit_tablespoon_converts(self, client):
        """raw_unit='c.à.s' + raw_quantity=2 → quantity_g=30 (2 × 15 g)."""
        food = _food(client, "Sauce soja")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Marinade",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 2.0, "raw_unit": "c.à.s"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 30.0

    def test_raw_unit_teaspoon_converts(self, client):
        """raw_unit='c.à.c' + raw_quantity=1 → quantity_g=5."""
        food = _food(client, "Sel fin")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Assaisonnement",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 1.0, "raw_unit": "c.à.c"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 5.0

    def test_no_quantity_at_all_defaults_to_100g(self, client):
        """Ni quantity_g ni raw_quantity fournis → 100 g par défaut."""
        food = _food(client, "Poivre noir")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Recette poivre",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"]},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 100.0

    def test_raw_unit_ml_converts_without_density(self, client):
        """raw_unit='ml' sans densité → 1 ml ≈ 1 g."""
        food = _food(client, "Lait")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Bechamel",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 250.0, "raw_unit": "ml"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 250.0

    def test_raw_unit_ml_uses_density_when_available(self, client):
        """raw_unit='ml' avec density=0.9 → 100 ml × 0.9 = 90 g."""
        food = _food(client, "Huile olive", density=0.9)
        resp = client.post("/api/v1/recipes/", json={
            "name": "Vinaigrette",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 100.0, "raw_unit": "ml"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 90.0

    def test_count_unit_uses_portion_weight(self, client):
        """Ingrédient compté (ex: 2 œufs) → portion_weight_g × raw_quantity."""
        food = _food(client, "Oeuf entier", portion_weight_g=60.0)
        resp = client.post("/api/v1/recipes/", json={
            "name": "Omelette",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 3.0, "raw_unit": None},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 180.0

    def test_invalid_food_id_returns_422_with_detail(self, client):
        """food_id inexistant → 422 avec le message mentionnant l'ID."""
        resp = client.post("/api/v1/recipes/", json={
            "name": "Recette invalide",
            "type": "simple",
            "ingredients_food": [
                {"food_id": 999999, "quantity_g": 100.0},
            ],
        })
        assert resp.status_code == 422
        assert "999999" in resp.json()["detail"]

    def test_update_recipe_also_validates_food_id(self, client):
        """PUT /{id} avec food_id invalide → 422 également."""
        food = _food(client, "Carotte")
        create = client.post("/api/v1/recipes/", json={
            "name": "Soupe",
            "type": "simple",
            "ingredients_food": [{"food_id": food["id"], "quantity_g": 200.0}],
        })
        recipe_id = create.json()["id"]

        resp = client.put(f"/api/v1/recipes/{recipe_id}", json={
            "name": "Soupe modifiee",
            "type": "simple",
            "ingredients_food": [{"food_id": 999999, "quantity_g": 200.0}],
        })
        assert resp.status_code == 422
        assert "999999" in resp.json()["detail"]

    def test_update_recipe_quantity_g_auto_computed(self, client):
        """PUT /{id} : raw_unit + raw_quantity suffisent, quantity_g calculé."""
        food = _food(client, "Pates")
        create = client.post("/api/v1/recipes/", json={
            "name": "Pasta",
            "type": "complete",
            "ingredients_food": [{"food_id": food["id"], "quantity_g": 100.0}],
        })
        recipe_id = create.json()["id"]

        resp = client.put(f"/api/v1/recipes/{recipe_id}", json={
            "name": "Pasta updated",
            "type": "complete",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 0.25, "raw_unit": "kg"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 250.0


# ===========================================================================
# Issue 2 — Endpoint POST /foods/match-ingredients
# ===========================================================================

class TestMatchIngredients:
    def test_empty_db_returns_null_matches(self, client):
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "boeuf hache", "quantity": 400.0, "unit": "g"}],
        })
        assert resp.status_code == 200
        r = resp.json()
        assert len(r) == 1
        assert r[0]["best_match"] is None
        assert r[0]["alternatives"] == []

    def test_exact_name_score_1(self, client):
        food = _food(client, "Boeuf hache")
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "Boeuf hache", "quantity": 400.0, "unit": "g"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["best_match"]["food_id"] == food["id"]
        assert r["best_match"]["score"] == 1.0
        assert r["best_match"]["match_type"] == "exact"
        assert r["quantity_g"] == 400.0

    def test_partial_name_finds_food(self, client):
        food = _food(client, "Lait entier")
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "lait", "quantity": 200.0, "unit": "ml"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["best_match"]["food_id"] == food["id"]
        assert r["quantity_g"] == 200.0  # ml sans densité → 1 g/ml

    def test_tablespoon_conversion_in_match(self, client):
        """3 c.à.s huile → quantity_g=45 (3 × 15 g)."""
        food = _food(client, "Huile olive")
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "huile olive", "quantity": 3.0, "unit": "c.à.s"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["quantity_g"] == 45.0

    def test_ml_with_density(self, client):
        """200 ml huile (density=0.9) → 180 g."""
        food = _food(client, "Huile tournesol", density=0.9)
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "huile tournesol", "quantity": 200.0, "unit": "ml"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["quantity_g"] == 180.0

    def test_unknown_unit_no_match_quantity_g_null(self, client):
        """Unité inconnue ET aucun aliment trouvé → best_food=None → quantity_g null."""
        # BD vide : pas de best_food → convert_to_grams("sachet", None) → None
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "xyzproduitinexistant", "quantity": 1.0, "unit": "sachet"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["quantity_g"] is None

    def test_unknown_unit_with_default_portion_weight(self, client):
        """Unité inconnue mais aliment trouvé (portion_weight=100 g) → 1 × 100 = 100."""
        food = _food(client, "Levure chimique")  # portion_weight_g=100 par défaut
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "Levure chimique", "quantity": 1.0, "unit": "sachet"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        # sachet inconnu → fallback portion_weight_g (100) × 1 = 100 g
        assert r["quantity_g"] == 100.0

    def test_unit_with_portion_weight(self, client):
        """Unité inconnue avec portion_weight → quantity × portion_weight."""
        food = _food(client, "Oeuf", portion_weight_g=60.0)
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "oeuf", "quantity": 2.0, "unit": "piece"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        # "piece" inconnu → portion_weight_g × raw_quantity = 60 × 2 = 120
        assert r["quantity_g"] == 120.0

    def test_multiple_ingredients(self, client):
        """Plusieurs ingrédients en une seule requête."""
        food1 = _food(client, "Tomate")
        food2 = _food(client, "Oignon")
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [
                {"product": "Tomate", "quantity": 200.0, "unit": "g"},
                {"product": "Oignon", "quantity": 1.0, "unit": None},
            ],
        })
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2
        matched_ids = {r["best_match"]["food_id"] for r in results if r["best_match"]}
        assert food1["id"] in matched_ids
        assert food2["id"] in matched_ids

    def test_alternatives_returned(self, client):
        """Plusieurs aliments similaires → alternatives non vides."""
        _food(client, "Tomate cerise")
        _food(client, "Tomate sechee")
        _food(client, "Tomate concentree")
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "tomate", "quantity": 100.0, "unit": "g"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["best_match"] is not None
        assert isinstance(r["alternatives"], list)
        # Au moins un aliment en alternative
        assert len(r["alternatives"]) >= 1

    def test_response_structure(self, client):
        """Chaque résultat a les champs attendus."""
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "quelque chose", "quantity": 50.0, "unit": "g"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert "product" in r
        assert "quantity_g" in r
        assert "best_match" in r
        assert "alternatives" in r

    def test_empty_product_string_handled(self, client):
        """product vide → best_match null, pas d'erreur 500."""
        resp = client.post("/api/v1/foods/match-ingredients", json={
            "ingredients": [{"product": "", "quantity": 100.0, "unit": "g"}],
        })
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["best_match"] is None
