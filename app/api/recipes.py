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
                quantity_g=ing.quantity_g,
                raw_quantity=ing.raw_quantity,
                raw_unit=ing.raw_unit,
                food_portion_id=ing.food_portion_id,
            )
            db.add(db_ing)
            
    # Ajouter les sous-recettes
    if recipe_in.ingredients_sub:
        for ing in recipe_in.ingredients_sub:
            db_ing = IngredientModel(
                recipe_id=db_recipe.id,
                sub_recipe_id=ing.sub_recipe_id,
                quantity_g=ing.quantity_g,
                raw_quantity=ing.raw_quantity,
                raw_unit=ing.raw_unit
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
    limit: int = 100,
    search: str = None
) -> Any:
    """
    Récupère la liste de toutes les recettes pour la Bibliothèque Globale.
    Triées par date de création décroissante (les plus récentes en premier).
    Retourne le header X-Total-Count pour la pagination côté client.
    """
    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder

    query = db.query(RecipeModel)
    if search:
        query = query.filter(RecipeModel.name.ilike(f"%{search}%"))
    total = query.count()
    recipes = query.order_by(RecipeModel.id.desc()).offset(skip).limit(limit).all()
    return JSONResponse(
        content=jsonable_encoder(recipes),
        headers={"X-Total-Count": str(total), "Access-Control-Expose-Headers": "X-Total-Count"},
    )

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

@router.put("/{recipe_id}", response_model=Recipe)
def update_recipe(
    *,
    db: Session = Depends(get_db),
    recipe_id: int,
    recipe_in: RecipeCreate,
) -> Any:
    """
    Mettre à jour une recette existante (nom, ingrédients, etc.) et recalculer les scores.
    """
    recipe = db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette non trouvée")

    # Mettre à jour les champs de base
    recipe.name = recipe_in.name
    recipe.description = recipe_in.description
    recipe.type = recipe_in.type
    recipe.visibility = recipe_in.visibility

    # Remplacer tous les ingrédients (delete + recreate)
    for old_ing in recipe.ingredients:
        db.delete(old_ing)
    db.flush()

    if recipe_in.ingredients_food:
        for ing in recipe_in.ingredients_food:
            db_ing = IngredientModel(
                recipe_id=recipe.id,
                food_id=ing.food_id,
                quantity_g=ing.quantity_g,
                raw_quantity=ing.raw_quantity,
                raw_unit=ing.raw_unit,
                food_portion_id=ing.food_portion_id,
            )
            db.add(db_ing)

    if recipe_in.ingredients_sub:
        for ing in recipe_in.ingredients_sub:
            db_ing = IngredientModel(
                recipe_id=recipe.id,
                sub_recipe_id=ing.sub_recipe_id,
                quantity_g=ing.quantity_g,
                raw_quantity=ing.raw_quantity,
                raw_unit=ing.raw_unit,
            )
            db.add(db_ing)

    db.commit()
    db.refresh(recipe)

    # Recalculer IS et DE
    recipe = calculate_recipe_nutrition(db, recipe)
    db.commit()
    db.refresh(recipe)

    return recipe

import uuid
from fastapi import BackgroundTasks
from pydantic import HttpUrl

from app.services.scraper import scrape_recipe_from_url
from app.schemas.scraper import TaskResponse, TaskStatus
from app.services.task_manager import create_task, update_task_status, get_task_status

def async_scrape_worker(task_id: str, url: str) -> None:
    """Exécute le scraping en arrière-plan et gère les erreurs."""
    try:
        data = scrape_recipe_from_url(url)
        update_task_status(task_id, "completed", data=data)
    except Exception as e:
        update_task_status(task_id, "failed", error=str(e))

@router.post("/import", status_code=202, response_model=TaskResponse)
def extract_recipe_from_url(url: HttpUrl, background_tasks: BackgroundTasks) -> Any:
    """
    Extrait les informations brutes d'une URL de recette (Schema.org) de manière asynchrone.
    Retourne immédiatement un task_id pour le suivi.
    """
    task_id = str(uuid.uuid4())
    create_task(task_id)
    background_tasks.add_task(async_scrape_worker, task_id, str(url))
    
    return TaskResponse(task_id=task_id, status="pending")

@router.get("/import/status/{task_id}", response_model=TaskStatus)
def get_scraping_status(task_id: str) -> Any:
    """
    Retourne l'état actuel d'une tâche d'extraction asynchrone.
    """
    task_info = get_task_status(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
        
    return TaskStatus(
        task_id=task_id,
        status=task_info["status"],
        data=task_info.get("data"),
        error=task_info.get("error")
    )
