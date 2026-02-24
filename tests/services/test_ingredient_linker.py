"""
Tests unitaires pour app/services/ingredient_linker.py

Couvre :
  - _normalize : suppression accents, minuscules, mots vides
  - _composite_score : score exact, token, seq
  - convert_to_grams : g, kg, c.à.s, c.à.c, ml+densité, comptage+portion, None
  - find_food_matches : exact, token, partiel, limite, DB vide, tri par score
"""
import pytest
from app.services.ingredient_linker import (
    _normalize,
    _composite_score,
    convert_to_grams,
    find_food_matches,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_food(name, *, density=None, portion_weight_g=None):
    """Duck-type minimal d'un objet Food pour tester convert_to_grams sans DB."""
    class _F:
        pass
    f = _F()
    f.density = density
    f.portion_weight_g = portion_weight_g
    return f


def _insert_food(db, name, energy_kcal=150.0):
    from app.models.food import Food
    food = Food(
        name=name,
        energy_kcal=energy_kcal,
        proteins_g=10.0,
        fat_g=5.0,
        carbohydrates_g=15.0,
        fiber_g=2.0,
        water_g=50.0,
    )
    db.add(food)
    db.commit()
    db.refresh(food)
    return food


# ===========================================================================
# _normalize
# ===========================================================================

class TestNormalize:
    def test_lowercase(self):
        # Les modificateurs culinaires (hache) sont conservés (non stop-words)
        assert _normalize("BOEUF HACHE") == "boeuf hache"

    def test_removes_accents(self):
        assert _normalize("été") == "ete"
        assert _normalize("fèves") == "feves"

    def test_ligature_oe(self):
        # "œ" est une ligature NFD-stable → remplacement explicite en "oe"
        assert _normalize("bœuf") == "boeuf"

    def test_removes_stop_words(self):
        assert _normalize("de la farine") == "farine"
        assert _normalize("sauce de soja") == "sauce soja"

    def test_removes_special_chars(self):
        result = _normalize("huile d'olive")
        assert "'" not in result
        assert "huile" in result
        assert "olive" in result

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_only_stop_words(self):
        assert _normalize("de du des") == ""


# ===========================================================================
# _composite_score
# ===========================================================================

class TestCompositeScore:
    def test_exact_match_score_1(self):
        # _composite_score attend un product_norm déjà normalisé
        norm = _normalize("Boeuf hache")   # "boeuf hache"
        assert _composite_score(norm, "Boeuf hache") == 1.0

    def test_no_common_tokens(self):
        score = _composite_score("pomme", "carotte")
        assert score < 0.3

    def test_partial_match_score_between_0_and_1(self):
        score = _composite_score("boeuf", "boeuf hache maigre")
        assert 0.0 < score < 1.0

    def test_higher_score_for_closer_name(self):
        # "tomate cerise" vs "tomate cerise" doit scorer plus haut que vs "tomate sechee"
        s1 = _composite_score("tomate cerise", "tomate cerise")
        s2 = _composite_score("tomate cerise", "tomate sechee")
        assert s1 > s2

    def test_empty_product_returns_0(self):
        assert _composite_score("", "boeuf") == 0.0

    def test_empty_food_returns_0(self):
        assert _composite_score("boeuf", "") == 0.0


# ===========================================================================
# convert_to_grams
# ===========================================================================

class TestConvertToGrams:
    def test_grams_direct(self):
        assert convert_to_grams(400.0, "g") == 400.0

    def test_grams_alias(self):
        assert convert_to_grams(200.0, "grammes") == 200.0

    def test_kilograms(self):
        assert convert_to_grams(1.5, "kg") == 1500.0

    def test_tablespoon(self):
        assert convert_to_grams(2.0, "c.à.s") == 30.0

    def test_tablespoon_variant_cas(self):
        # Parser renvoie parfois "c.à.s" — alias doit fonctionner
        assert convert_to_grams(1.0, "c.à.s") == 15.0

    def test_teaspoon(self):
        assert convert_to_grams(1.0, "c.à.c") == 5.0

    def test_teaspoon_variant_cac(self):
        assert convert_to_grams(2.0, "c.à.c") == 10.0

    def test_milliliter_no_density(self):
        # Sans densité, 1 ml ≈ 1 g
        assert convert_to_grams(100.0, "ml") == 100.0

    def test_milliliter_with_density(self):
        food = _make_food("huile", density=0.9)
        assert convert_to_grams(100.0, "ml", food) == 90.0

    def test_centiliter(self):
        assert convert_to_grams(10.0, "cl") == 100.0

    def test_liter(self):
        assert convert_to_grams(0.5, "l") == 500.0

    def test_count_with_portion_weight(self):
        food = _make_food("oeuf", portion_weight_g=60.0)
        assert convert_to_grams(2.0, None, food) == 120.0

    def test_count_without_food_returns_none(self):
        assert convert_to_grams(2.0, None) is None

    def test_unknown_unit_no_food_returns_none(self):
        assert convert_to_grams(3.0, "sachet") is None

    def test_unknown_unit_with_portion_returns_value(self):
        food = _make_food("levure", portion_weight_g=7.0)
        assert convert_to_grams(1.0, "sachet", food) == 7.0

    def test_none_quantity_returns_none(self):
        assert convert_to_grams(None, "g") is None

    def test_zero_quantity_returns_none(self):
        assert convert_to_grams(0.0, "g") is None

    def test_pinch(self):
        result = convert_to_grams(1.0, "pincée")
        assert result == 0.5

    def test_glass(self):
        assert convert_to_grams(1.0, "verre") == 200.0

    def test_cup(self):
        assert convert_to_grams(1.0, "tasse") == 240.0


# ===========================================================================
# find_food_matches  (nécessite db_session)
# ===========================================================================

class TestFindFoodMatches:
    def test_empty_db_returns_empty(self, db_session):
        results = find_food_matches("boeuf hache", db_session)
        assert results == []

    def test_empty_product_returns_empty(self, db_session):
        _insert_food(db_session, "Boeuf hache")
        assert find_food_matches("", db_session) == []
        assert find_food_matches("   ", db_session) == []

    def test_exact_match_score_1(self, db_session):
        food = _insert_food(db_session, "Boeuf hache")
        results = find_food_matches("Boeuf hache", db_session)
        assert len(results) >= 1
        assert results[0]["food_id"] == food.id
        assert results[0]["score"] == 1.0
        assert results[0]["match_type"] == "exact"

    def test_exact_match_case_insensitive(self, db_session):
        food = _insert_food(db_session, "Farine de ble")
        results = find_food_matches("farine de ble", db_session)
        assert results[0]["food_id"] == food.id
        assert results[0]["score"] == 1.0

    def test_token_match_finds_food(self, db_session):
        food = _insert_food(db_session, "Boeuf hache maigre 5 pourcent")
        results = find_food_matches("boeuf hache", db_session)
        assert len(results) >= 1
        assert results[0]["food_id"] == food.id
        assert results[0]["score"] > 0.5

    def test_partial_token_finds_food(self, db_session):
        """Un seul token discriminant suffit à trouver l'aliment."""
        food = _insert_food(db_session, "Lait entier")
        results = find_food_matches("lait", db_session)
        assert any(r["food_id"] == food.id for r in results)

    def test_multiple_foods_sorted_by_score(self, db_session):
        _insert_food(db_session, "Tomate cerise")
        _insert_food(db_session, "Tomate sechee")
        _insert_food(db_session, "Tomate concentree")
        results = find_food_matches("Tomate cerise", db_session)
        assert len(results) >= 1
        # Le premier doit être "Tomate cerise" (score le plus haut)
        assert "cerise" in results[0]["food_name"].lower()
        # Scores triés décroissants
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_limit_respected(self, db_session):
        for i in range(10):
            _insert_food(db_session, f"Boeuf variante {i}")
        results = find_food_matches("boeuf", db_session, limit=3)
        assert len(results) <= 3

    def test_no_duplicate_ids(self, db_session):
        _insert_food(db_session, "Poulet blanc")
        _insert_food(db_session, "Poulet roti")
        results = find_food_matches("poulet", db_session)
        ids = [r["food_id"] for r in results]
        assert len(ids) == len(set(ids))

    def test_irrelevant_query_returns_empty_or_low_score(self, db_session):
        _insert_food(db_session, "Sucre blanc")
        results = find_food_matches("xyzabc123", db_session)
        # Soit vide, soit scores très bas
        for r in results:
            assert r["score"] < 0.5

    def test_score_field_present(self, db_session):
        _insert_food(db_session, "Riz basmati")
        results = find_food_matches("riz", db_session)
        for r in results:
            assert "food_id" in r
            assert "food_name" in r
            assert "score" in r
            assert "match_type" in r
            assert 0.0 <= r["score"] <= 1.0
