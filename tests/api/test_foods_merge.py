import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.food import Food
from app.models.recipe import Recipe, RecipeIngredient

def test_merge_foods_success(client: TestClient, db_session: Session):
    # 1. Setup: Créer une Cible et deux Sources (Brouillons)
    target = Food(name="Tomate (Valide)", energy_kcal=18)
    source1 = Food(name="Tomatres", is_draft=True)
    source2 = Food(name="Tomat", is_draft=True)
    db_session.add_all([target, source1, source2])
    db_session.commit()
    
    # 2. Setup: Créer une Recette liée aux Sources
    recipe = Recipe(name="Salade de Tomatres", description="Test")
    db_session.add(recipe)
    db_session.commit()
    
    ing1 = RecipeIngredient(recipe_id=recipe.id, food_id=source1.id, quantity_g=200, raw_quantity=2, raw_unit="piece")
    ing2 = RecipeIngredient(recipe_id=recipe.id, food_id=source2.id, quantity_g=100, raw_quantity=1, raw_unit="piece")
    db_session.add_all([ing1, ing2])
    db_session.commit()

    # 3. Execution: Fusionner les deux brouillons vers la cible
    response = client.post(
        "/api/v1/foods/merge", 
        json={"target_id": target.id, "source_ids": [source1.id, source2.id]}
    )
    
    # 4. Assertions
    assert response.status_code == 200
    assert response.json()["message"] == "2 aliments fusionnés avec succès"
    
    # Vérification BDD: Les sources doivent être supprimées
    assert db_session.query(Food).filter(Food.id == source1.id).first() is None
    assert db_session.query(Food).filter(Food.id == source2.id).first() is None
    
    # Vérification BDD: La cible existe toujours
    assert db_session.query(Food).filter(Food.id == target.id).first() is not None
    
    # Vérification BDD: Les relations de la recette doivent avoir été réattribuées à la Target
    db_session.refresh(recipe)
    for ing in recipe.ingredients:
        assert ing.food_id == target.id

def test_merge_foods_invalid_target(client: TestClient, db_session: Session):
    response = client.post(
        "/api/v1/foods/merge", 
        json={"target_id": 99999, "source_ids": [1]}
    )
    assert response.status_code == 404
    assert "cible non trouvé" in response.json()["detail"].lower()

def test_merge_foods_empty_sources(client: TestClient, db_session: Session):
    target = Food(name="Tomate (Valide)", energy_kcal=18)
    db_session.add(target)
    db_session.commit()
    
    response = client.post(
        "/api/v1/foods/merge", 
        json={"target_id": target.id, "source_ids": []}
    )
    assert response.status_code == 400
    assert "au moins un" in response.json()["detail"].lower()
