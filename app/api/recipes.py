from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.recipe import Recipe as RecipeModel
from app.models.recipe import RecipeIngredient as IngredientModel
from app.schemas.recipe import Recipe, RecipeCreate
from app.services.nutrition import calculate_recipe_nutrition

router = APIRouter()

@router.post("/", response_model=Recipe)
def create_recipe(
    *,
    db: Session = Depends(get_db),
    recipe_in: RecipeCreate,
) -> Any:
    """
    Créer une nouvelle recette et calculer automatiquement ses scores IS et DE.
    """
    recipe_data = recipe_in.model_dump(exclude={"ingredients_food", "ingredients_sub"})
    db_recipe = RecipeModel(**recipe_data)
    db.add(db_recipe)
    db.flush() # Pour avoir l'ID
    
    # Ajouter les ingrédients bruts
    if recipe_in.ingredients_food:
        for ing in recipe_in.ingredients_food:
            db_ing = IngredientModel(
                recipe_id=db_recipe.id,
                food_id=ing.food_id,
                quantity_g=ing.quantity_g
            )
            db.add(db_ing)
            
    # Ajouter les sous-recettes
    if recipe_in.ingredients_sub:
        for ing in recipe_in.ingredients_sub:
            db_ing = IngredientModel(
                recipe_id=db_recipe.id,
                sub_recipe_id=ing.sub_recipe_id,
                quantity_g=ing.quantity_g
            )
            db.add(db_ing)
            
    db.commit()
    db.refresh(db_recipe)
    
    # Calculer l'Indice de Satiété et la Densité Energétique
    db_recipe = calculate_recipe_nutrition(db, db_recipe)
    db.commit()
    db.refresh(db_recipe)
    
    return db_recipe

@router.get("/", response_model=List[Recipe])
def get_all_recipes(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Récupère la liste de toutes les recettes pour la Bibliothèque Globale.
    """
    recipes = db.query(RecipeModel).offset(skip).limit(limit).all()
    return recipes

@router.get("/{recipe_id}", response_model=Recipe)
def read_recipe(
    *,
    db: Session = Depends(get_db),
    recipe_id: int,
) -> Any:
    """
    Récupérer une recette complète avec ses ingrédients et ses scores.
    """
    recipe = db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette non trouvée")
    return recipe

from pydantic import HttpUrl
from app.services.scraper import scrape_recipe_from_url

@router.post("/scrape")
def extract_recipe_from_url(url: HttpUrl) -> Any:
    """
    Extrait les informations brutes d'une URL de recette (Schema.org).
    L'utilisateur devra ensuite mapper ces données brutes avec les aliments de base (Food) pour créer une recette complète.
    """
    try:
        data = scrape_recipe_from_url(str(url))
        return {
            "success": True,
            "data": data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
