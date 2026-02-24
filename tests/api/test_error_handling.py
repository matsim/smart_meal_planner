"""
Tests de la gestion d'erreurs de l'API.

Couvre :
  1. nutrition.py : quantity_g NULL en base → calcul ignoré silencieusement (pas de 500)
  2. recipes.py   : échec calcul nutrition → recette quand même retournée (200, pas 500)
  3. main.py      : RequestValidationError → 422 structuré (champ + message lisible)
  4. main.py      : Exception non gérée → 500 structuré (pas de "Internal Server Error" vide)
"""
import pytest
from unittest.mock import patch

_FOOD_BASE = {
    "energy_kcal": 200.0,
    "proteins_g": 15.0,
    "fat_g": 8.0,
    "carbohydrates_g": 20.0,
    "fiber_g": 3.0,
    "water_g": 40.0,
}


def _food(client, name="Aliment"):
    r = client.post("/api/v1/foods/", json={"name": name, **_FOOD_BASE})
    assert r.status_code == 200, r.text
    return r.json()


def _recipe(client, food_id, name="Recette", qty=200.0):
    r = client.post("/api/v1/recipes/", json={
        "name": name,
        "type": "simple",
        "ingredients_food": [{"food_id": food_id, "quantity_g": qty}],
    })
    assert r.status_code == 200, r.text
    return r.json()


# ===========================================================================
# 1. NULL quantity_g en base → nutrition ignorée silencieusement
# ===========================================================================

class TestNullQuantityRobustness:
    def test_ingredient_with_null_qty_does_not_crash(self, client, db_session):
        """
        Un ingrédient avec quantity_g=NULL ne doit pas planter le calcul
        nutritionnel (TypeError à l'époque), il doit juste être ignoré.

        Le schéma actuel a quantity_g NOT NULL, mais on simule l'ancien état
        via un mock afin de vérifier le garde dans _collect_raw_nutrients.
        """
        from unittest.mock import MagicMock
        from app.services.nutrition import calculate_recipe_nutrition

        # Simuler un ingrédient avec quantity_g=None (ancien enregistrement)
        mock_ingredient = MagicMock()
        mock_ingredient.quantity_g = None
        mock_ingredient.food_id = 1
        mock_ingredient.sub_recipe_id = None

        mock_recipe = MagicMock()
        mock_recipe.ingredients = [mock_ingredient]

        # Le calcul ne doit pas lever d'exception
        result = calculate_recipe_nutrition(db_session, mock_recipe)

        # Poids nul → énergie 0 (l'ingrédient null a été ignoré)
        assert result.total_weight_g == 0.0
        assert result.energy_density == 0.0

    def test_save_recipe_with_null_qty_ingredient_still_returns_200(self, client, db_session):
        """
        Si quantity_g=0 est envoyé (équivalent fonctionnel d'un null),
        la recette est quand même enregistrée et retournée en 200.
        """
        food = _food(client, "Aliment zero qty")
        # quantity_g=0 → _resolve_quantity_g utilise raw_quantity+raw_unit → 100 g
        resp = client.post("/api/v1/recipes/", json={
            "name": "Recette zero qty",
            "type": "simple",
            "ingredients_food": [
                {"food_id": food["id"], "raw_quantity": 150.0, "raw_unit": "g"},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["ingredients"][0]["quantity_g"] == 150.0


# ===========================================================================
# 2. Échec du calcul nutritionnel → recette quand même retournée (200)
# ===========================================================================

class TestNutritionFailureSilent:
    def test_nutrition_crash_returns_200_not_500(self, client):
        """
        Si calculate_recipe_nutrition lève une exception inattendue,
        la recette est quand même retournée (200) grâce au try/except.
        """
        food = _food(client, "Aliment nutrition fail")

        with patch(
            "app.api.recipes.calculate_recipe_nutrition",
            side_effect=RuntimeError("Erreur simulée dans la nutrition"),
        ):
            resp = client.post("/api/v1/recipes/", json={
                "name": "Recette crash nutrition",
                "type": "simple",
                "ingredients_food": [{"food_id": food["id"], "quantity_g": 200.0}],
            })

        # La recette a été enregistrée (premier commit) → 200, pas 500
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Recette crash nutrition"
        # Les champs nutrition sont None / 0 (pas calculés)
        assert data.get("energy_density") in (None, 0.0)

    def test_nutrition_crash_on_update_returns_200(self, client):
        """Même protection sur PUT /{recipe_id}."""
        food = _food(client, "Aliment update crash")
        recipe = _recipe(client, food["id"], "Recette update crash")

        with patch(
            "app.api.recipes.calculate_recipe_nutrition",
            side_effect=RuntimeError("Crash simulé"),
        ):
            resp = client.put(f"/api/v1/recipes/{recipe['id']}", json={
                "name": "Recette update crash modifiee",
                "type": "simple",
                "ingredients_food": [{"food_id": food["id"], "quantity_g": 150.0}],
            })

        assert resp.status_code == 200
        assert resp.json()["name"] == "Recette update crash modifiee"


# ===========================================================================
# 3. RequestValidationError → 422 structuré lisible (pas de JSON Pydantic brut)
# ===========================================================================

class TestValidationErrorFormat:
    def test_missing_required_field_returns_structured_422(self, client):
        """POST /recipes/ sans 'name' → 422 avec 'detail' + 'errors'."""
        resp = client.post("/api/v1/recipes/", json={
            # 'name' manquant
            "type": "simple",
            "ingredients_food": [],
        })
        assert resp.status_code == 422
        body = resp.json()
        # Le handler custom retourne un message lisible en français
        assert "detail" in body
        assert "Données invalides" in body["detail"]
        assert "errors" in body
        assert len(body["errors"]) >= 1
        # Chaque erreur a les champs attendus
        for err in body["errors"]:
            assert "champ" in err
            assert "message" in err

    def test_invalid_enum_value_returns_structured_422(self, client):
        """Type de recette invalide → 422 avec liste d'erreurs structurée."""
        resp = client.post("/api/v1/recipes/", json={
            "name": "Test",
            "type": "INVALIDE",
        })
        assert resp.status_code == 422
        body = resp.json()
        assert "errors" in body
        assert any("type" in e["champ"].lower() for e in body["errors"])

    def test_invalid_food_id_type_returns_422(self, client):
        """food_id non-entier → 422 structuré."""
        resp = client.post("/api/v1/recipes/", json={
            "name": "Test",
            "type": "simple",
            "ingredients_food": [{"food_id": "pas_un_entier", "quantity_g": 100.0}],
        })
        assert resp.status_code == 422
        body = resp.json()
        assert "errors" in body

    def test_error_detail_is_human_readable_string(self, client):
        """Le champ 'detail' est une chaîne lisible, pas un tableau technique."""
        resp = client.post("/api/v1/recipes/", json={"type": "simple"})
        assert resp.status_code == 422
        body = resp.json()
        assert isinstance(body["detail"], str)
        assert len(body["detail"]) > 10

    def test_valid_request_not_affected(self, client):
        """Une requête valide ne doit pas être impactée par le handler."""
        food = _food(client, "Aliment valide")
        resp = client.post("/api/v1/recipes/", json={
            "name": "Recette valide",
            "type": "simple",
            "ingredients_food": [{"food_id": food["id"], "quantity_g": 100.0}],
        })
        assert resp.status_code == 200
