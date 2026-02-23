from sqlalchemy.orm import Session
from app.models.recipe import Recipe, RecipeIngredient
from app.models.food import Food

def calculate_recipe_nutrition(db: Session, recipe: Recipe) -> Recipe:
    """
    Calcule la Densité Energétique (DE) et l'Indice de Satiété (IS) pour une recette.
    IS = (protéines_g * 1.5) + (fibres_g * 2.5) + (volume_eau_g * 0.5) - (densité_énergétique * 10)
    """
    total_weight_g = 0.0
    total_kcal = 0.0
    total_proteins_g = 0.0
    total_fiber_g = 0.0
    total_water_g = 0.0
    
    # Parcourir les ingrédients
    for ingredient in recipe.ingredients:
        qty = ingredient.quantity_g
        
        if ingredient.food_id:
            # Aliment brut
            food = db.query(Food).filter(Food.id == ingredient.food_id).first()
            if not food:
                continue
                
            # Les valeurs de Food sont pour 100g
            ratio = qty / 100.0
            
            # Prise en compte du rendement de cuisson (yield_factor) pour le poids final
            final_weight = qty * food.yield_factor
            
            total_weight_g += final_weight
            total_kcal += food.energy_kcal * ratio
            total_proteins_g += food.proteins_g * ratio
            total_fiber_g += food.fiber_g * ratio
            total_water_g += food.water_g * ratio
            
        elif ingredient.sub_recipe_id:
            # Sous-recette (récursive)
            sub_recipe = db.query(Recipe).filter(Recipe.id == ingredient.sub_recipe_id).first()
            if not sub_recipe:
                continue
            
            # Pour simplifier, on suppose que la qty donnée est le poids final désiré de la sous-recette.
            # Normalement il faudrait calculer le ratio poids total sous-recette / qty demandée.
            # TODO: Implémenter logic récursive complète si nécessaire
            pass

    if total_weight_g == 0:
        recipe.energy_density = 0.0
        recipe.satiety_index = 0.0
        return recipe

    # Normaliser toutes les valeurs à 100g de recette finale
    ratio = 100.0 / total_weight_g
    prot_per_100  = total_proteins_g * ratio
    fiber_per_100 = total_fiber_g    * ratio
    water_per_100 = total_water_g    * ratio

    # Densité énergétique en kcal par 100g (plus lisible que kcal/g)
    de = (total_kcal / total_weight_g) * 100   # kcal / 100g

    # Indice de satiété (scores per 100g, comparables entre recettes)
    # Plage attendue : -10 → +150 environ
    is_score = (prot_per_100 * 1.5) + (fiber_per_100 * 2.5) + (water_per_100 * 0.5) - (de * 0.1)

    recipe.energy_density = round(de, 1)
    recipe.satiety_index  = round(is_score, 1)

    if de > 0:
        recipe.internal_nutrition_score = round(is_score / de * 100, 1)
    else:
        recipe.internal_nutrition_score = 0.0

    return recipe
