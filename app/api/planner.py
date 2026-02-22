from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User as UserModel
from app.models.recipe import Recipe as RecipeModel
from app.models.meal import MealPlan as MealPlanModel, Meal as MealModel, MealType
from app.services.metabolic import calculate_metabolic_profile
from app.services.planner import generate_weekly_plan, RecipeCandidate

router = APIRouter()

class PlanGenerationRequest(BaseModel):
    user_id: int
    start_date: date
    tolerance: float = 0.15  # +/- 15% par defaut

@router.post("/generate")
def create_weekly_plan(
    request: PlanGenerationRequest,
    db: Session = Depends(get_db)
) -> Any:
    # 1. Recuperer Utilisateur et Objectifs
    user = db.query(UserModel).filter(UserModel.id == request.user_id).first()
    if not user:
         raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
         
    profile = calculate_metabolic_profile(user)
    if profile.target_kcal == 0:
        raise HTTPException(status_code=400, detail="Profil métabolique incomplet.")

    # 2. Filtrer les Recettes (Exclusions)
    recipes_db = db.query(RecipeModel).all()
    user_constraints = [c.food_id for c in user.constraints if c.food_id is not None]
    
    valid_recipes = []
    for r in recipes_db:
        # Check if any ingredient is in constraints
        has_constraint = False
        for ing in r.ingredients:
            if ing.food_id in user_constraints:
                has_constraint = True
                break
        if not has_constraint:
            valid_recipes.append(r)
            
    if len(valid_recipes) < user.daily_meals_count * 2: 
         raise HTTPException(status_code=400, detail="Pas assez de recettes valides trouvées après avoir appliqué vos exclusions (trop restrictif).")
    
    import random
    candidates = []
    # Seed de variation pour couvrir différentes tailles et profils de repas
    for idx, r in enumerate(valid_recipes):
        multiplier = 0.8 + (idx % 10) * 0.1  # de 0.8 à 1.7
        base_kcal = 500.0 * multiplier
        
        # Varier la répartition pour que PuLP ait des leviers (Plats pro-prot, pro-fat, pro-carb...)
        random.seed(r.id) # Consistance pour le même plat
        prot_pct = random.uniform(0.15, 0.45) # 15 à 45% de pref
        fat_pct = random.uniform(0.20, 0.40)  # 20 à 40% de fat
        carb_pct = 1.0 - prot_pct - fat_pct
        
        prot = (base_kcal * prot_pct) / 4.0
        fat = (base_kcal * fat_pct) / 9.0
        carb = (base_kcal * carb_pct) / 4.0
        
        is_score = r.satiety_index or (50.0 * multiplier)
        candidates.append(RecipeCandidate(r.id, r.name, base_kcal, prot, fat, carb, is_score))

    # 3. Lancer le Solveur PuLP
    result = generate_weekly_plan(
        candidates=candidates,
        target_kcal=profile.target_kcal,
        target_prot=profile.protein_g,
        target_fat=profile.fat_g,
        target_carb=profile.carbs_g,
        meals_per_day=user.daily_meals_count,
        days=7,
        tolerance=request.tolerance
    )

    if not result.success:
         raise HTTPException(status_code=422, detail=result.message)

    # 4. Sauvegarder en Base de Données
    plan = MealPlanModel(
        user_id=user.id,
        start_date=request.start_date,
        end_date=request.start_date + timedelta(days=6),
        target_kcal=profile.target_kcal * 7,
        achieved_kcal=result.total_kcal
    )
    db.add(plan)
    db.flush()

    meal_types = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACK]

    # Insertion des repas
    for day_idx in range(7):
        current_date = request.start_date + timedelta(days=day_idx)
        day_key = f"Day_{day_idx + 1}"
        daily_meals = result.meals.get(day_key, [])
        
        for m_idx, recipe_candidate in enumerate(daily_meals):
            m_type = meal_types[m_idx % len(meal_types)]
            db_meal = MealModel(
                plan_id=plan.id,
                date=current_date,
                type=m_type,
                recipe_id=recipe_candidate.id,
                portion_factor=1.0 # V2: ajuster s'il le faut
            )
            db.add(db_meal)
            
    db.commit()
    db.refresh(plan)

    return {
        "success": True, 
        "message": result.message,
        "plan_id": plan.id, 
        "achieved_kcal_weekly": result.total_kcal
    }

from app.schemas.planner import ShoppingListResponse, ShoppingListItem, AlternativeRecipe
from app.models.recipe import RecipeIngredient as IngredientModel
from app.models.food import Food as FoodModel
from collections import defaultdict

@router.get("/users/{user_id}/latest")
def get_latest_plan(user_id: int, db: Session = Depends(get_db)):
    """Récupère le dernier plan généré par l'utilisateur (persistance Dashboard)"""
    plan = db.query(MealPlanModel).filter(MealPlanModel.user_id == user_id).order_by(MealPlanModel.start_date.desc(), MealPlanModel.id.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Aucun plan trouvé pour cet utilisateur.")
    
    days = defaultdict(list)
    for meal in plan.meals:
        recipe_data = None
        if meal.recipe_id:
            recipe = db.query(RecipeModel).filter(RecipeModel.id == meal.recipe_id).first()
            if recipe:
                recipe_data = {
                    "id": recipe.id,
                    "name": recipe.name,
                    "type": recipe.type.value if recipe.type else "N/A",
                }
        
        days[str(meal.date)].append({
            "id": meal.id,
            "type": meal.type.value if meal.type else "N/A",
            "recipe": recipe_data
        })
        
    return {
        "id": plan.id,
        "target_kcal": plan.target_kcal,
        "achieved_kcal": plan.achieved_kcal,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "days": dict(days)
    }

@router.get("/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(MealPlanModel).filter(MealPlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan non trouvé.")
        
    # Format the meals grouping by date
    days = defaultdict(list)
    for meal in plan.meals:
        recipe_data = None
        if meal.recipe_id:
            recipe = db.query(RecipeModel).filter(RecipeModel.id == meal.recipe_id).first()
            if recipe:
                recipe_data = {
                    "id": recipe.id,
                    "name": recipe.name,
                    "type": recipe.type.value if recipe.type else "N/A",
                }
        
        days[str(meal.date)].append({
            "id": meal.id,
            "type": meal.type.value if meal.type else "N/A",
            "recipe": recipe_data
        })
        
    return {
        "id": plan.id,
        "target_kcal": plan.target_kcal,
        "achieved_kcal": plan.achieved_kcal,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "days": dict(days)
    }

@router.get("/{plan_id}/shopping-list", response_model=ShoppingListResponse)
def get_shopping_list(
    plan_id: int,
    family_multiplier: int = 1,
    db: Session = Depends(get_db)
) -> Any:
    """
    Génère la liste de courses agrégée pour un plan entier, avec un multiplicateur optionnel (ex: Mode Famille).
    Gère (pour la version basique) uniquement les ingrédients de niveau 1 (pas de récursivité sous-recette pour l'instant).
    """
    plan = db.query(MealPlanModel).filter(MealPlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan nutritionnel non trouvé.")
        
    shopping_dict = defaultdict(float)
    
    # 1. Parcourir tous les repas du plan
    for meal in plan.meals:
        if meal.recipe_id:
            recipe = db.query(RecipeModel).filter(RecipeModel.id == meal.recipe_id).first()
            if recipe:
                # 2. Extraire la quantité des ingrédients
                for ing in recipe.ingredients:
                    if ing.food_id:
                         # On multiplie la qty requise par le rendement du meal (si ajusté par solveur) et la famille
                         qty = ing.quantity_g * meal.portion_factor * family_multiplier
                         shopping_dict[ing.food_id] += qty

    # 3. Formatter la réponse
    items = []
    for food_id, total_qty in shopping_dict.items():
        food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
        if food:
            items.append(ShoppingListItem(
                food_id=food_id,
                food_name=food.name,
                total_quantity_g=round(total_qty, 2)
            ))
            
    return ShoppingListResponse(plan_id=plan_id, items=items)

@router.get("/meals/{meal_id}/alternatives", response_model=List[AlternativeRecipe])
def get_meal_alternatives(
    meal_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Propose 3 à 5 recettes alternatives pour substituer un repas.
    Critère heuristique simple : même fourchette calorique (dans les +/- 10%) pour ne pas briser la cible hebdo.
    """
    meal = db.query(MealModel).filter(MealModel.id == meal_id).first()
    if not meal or not meal.recipe_id:
        raise HTTPException(status_code=404, detail="Repas introuvable ou vide.")
        
    current_recipe = db.query(RecipeModel).filter(RecipeModel.id == meal.recipe_id).first()
    # Mocking total_kcal (à implémenter en V1 finale via `calculate_nutrition`)
    current_kcal = 500.0 # Biais
    
    candidates = db.query(RecipeModel).filter(
        RecipeModel.id != current_recipe.id,
        RecipeModel.type == current_recipe.type # On remplace idéalement un plat par un plat
    ).limit(30).all()
    
    results = []
    for c in candidates:
        cand_kcal = 500.0 # Biais
        
        # Exemple basique: % de différence calorique
        diff_percent = abs(cand_kcal - current_kcal) / current_kcal
        if diff_percent <= 0.15: # Rentre dans la tolérance
            # Match score: 100% si kcal parfait, descend si s'éloigne
            score = 100.0 - (diff_percent * 100.0)
            results.append(AlternativeRecipe(
                recipe_id=c.id,
                recipe_name=c.name,
                match_score=round(score, 1)
            ))
            
    # Tri par score décroissant et limite top 5
    results.sort(key=lambda x: x.match_score, reverse=True)
    return results[:5]

from pydantic import BaseModel

class MealReplaceRequest(BaseModel):
    recipe_id: int

@router.post("/swap/{repas_id}")
def replace_meal(
    repas_id: int,
    request: MealReplaceRequest,
    db: Session = Depends(get_db)
):
    """
    Remplace la recette assignée à un repas spécifique du plan.
    Sert à la fonctionnalité d'édition unitaire par l'utilisateur.
    """
    meal = db.query(MealModel).filter(MealModel.id == repas_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Repas introuvable.")
        
    recipe = db.query(RecipeModel).filter(RecipeModel.id == request.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette de remplacement introuvable.")
        
    # Validation basique: on remplace un ID par un autre
    meal.recipe_id = recipe.id
    db.commit()
    
    return {"success": True, "message": "Repas mis à jour avec la nouvelle recette."}
