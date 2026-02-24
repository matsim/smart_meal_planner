from sqlalchemy.orm import Session
from app.models.recipe import Recipe, RecipeIngredient
from app.models.food import Food


def _collect_raw_nutrients(db: Session, recipe: Recipe, depth: int = 0):
    """
    Collecte récursivement les nutriments bruts d'une recette (non normalisés).
    Retourne : (weight_g, kcal, proteins_g, fat_g, carbs_g, fiber_g, water_g)
    depth : protection anti-boucle infinie (max 5 niveaux).
    """
    if depth > 5:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    total_weight_g  = 0.0
    total_kcal      = 0.0
    total_proteins  = 0.0
    total_fat       = 0.0
    total_carbs     = 0.0
    total_fiber     = 0.0
    total_water     = 0.0

    for ingredient in recipe.ingredients:
        qty = ingredient.quantity_g

        if ingredient.food_id:
            food = db.query(Food).filter(Food.id == ingredient.food_id).first()
            if not food:
                continue
            ratio = qty / 100.0
            total_weight_g  += qty * food.yield_factor
            total_kcal      += food.energy_kcal       * ratio
            total_proteins  += food.proteins_g         * ratio
            total_fat       += food.fat_g              * ratio
            total_carbs     += food.carbohydrates_g    * ratio
            total_fiber     += food.fiber_g            * ratio
            total_water     += food.water_g            * ratio

        elif ingredient.sub_recipe_id:
            sub = db.query(Recipe).filter(Recipe.id == ingredient.sub_recipe_id).first()
            if not sub:
                continue
            sub_w, sub_kcal, sub_prot, sub_fat, sub_carbs, sub_fiber, sub_water = \
                _collect_raw_nutrients(db, sub, depth + 1)
            if sub_w > 0:
                scale = qty / sub_w
                total_weight_g += qty          # poids demandé = poids apporté
                total_kcal     += sub_kcal  * scale
                total_proteins += sub_prot  * scale
                total_fat      += sub_fat   * scale
                total_carbs    += sub_carbs * scale
                total_fiber    += sub_fiber * scale
                total_water    += sub_water * scale

    return total_weight_g, total_kcal, total_proteins, total_fat, total_carbs, total_fiber, total_water


def _compute_dietary_flags(db: Session, recipe: Recipe):
    """
    Dérive les flags diététiques de la recette depuis ses ingrédients.
    Un flag vaut False dès qu'un aliment (ou sous-recette) ne le respecte pas.
    """
    is_vegetarian  = True
    is_vegan       = True
    is_gluten_free = True
    is_lactose_free = True

    for ingredient in recipe.ingredients:
        if ingredient.food_id:
            food = db.query(Food).filter(Food.id == ingredient.food_id).first()
            if food:
                if not food.is_vegetarian:  is_vegetarian  = False
                if not food.is_vegan:       is_vegan       = False
                if not food.is_gluten_free: is_gluten_free = False
                if not food.is_lactose_free: is_lactose_free = False
        elif ingredient.sub_recipe_id:
            sub = db.query(Recipe).filter(Recipe.id == ingredient.sub_recipe_id).first()
            if sub:
                if not sub.is_vegetarian:  is_vegetarian  = False
                if not sub.is_vegan:       is_vegan       = False
                if not sub.is_gluten_free: is_gluten_free = False
                if not sub.is_lactose_free: is_lactose_free = False

    return is_vegetarian, is_vegan, is_gluten_free, is_lactose_free


def calculate_recipe_nutrition(db: Session, recipe: Recipe) -> Recipe:
    """
    Calcule et stocke sur la recette :
    - Densité Energétique (kcal/100g)
    - Indice de Satiété (IS/100g)
    - Macros par 100g (protéines, lipides, glucides)
    - Poids total cuit (g)
    - Flags diététiques dérivés des ingrédients
    Gère les sous-recettes récursivement (jusqu'à 5 niveaux).
    """
    total_weight_g, total_kcal, total_proteins, total_fat, total_carbs, total_fiber, total_water = \
        _collect_raw_nutrients(db, recipe)

    # Flags diéto (calculés indépendamment du poids)
    recipe.is_vegetarian, recipe.is_vegan, recipe.is_gluten_free, recipe.is_lactose_free = \
        _compute_dietary_flags(db, recipe)

    if total_weight_g == 0:
        recipe.energy_density    = 0.0
        recipe.satiety_index     = 0.0
        recipe.total_weight_g    = 0.0
        recipe.proteins_per_100g = 0.0
        recipe.fat_per_100g      = 0.0
        recipe.carbs_per_100g    = 0.0
        return recipe

    # Normalisation à 100g
    ratio         = 100.0 / total_weight_g
    prot_per_100  = total_proteins * ratio
    fat_per_100   = total_fat      * ratio
    carbs_per_100 = total_carbs    * ratio
    fiber_per_100 = total_fiber    * ratio
    water_per_100 = total_water    * ratio

    de       = (total_kcal / total_weight_g) * 100          # kcal / 100g
    is_score = (prot_per_100 * 1.5) + (fiber_per_100 * 2.5) \
             + (water_per_100 * 0.5) - (de * 0.1)

    recipe.energy_density            = round(de, 1)
    recipe.satiety_index             = round(is_score, 1)
    recipe.total_weight_g            = round(total_weight_g, 1)
    recipe.proteins_per_100g         = round(prot_per_100, 2)
    recipe.fat_per_100g              = round(fat_per_100, 2)
    recipe.carbs_per_100g            = round(carbs_per_100, 2)
    recipe.internal_nutrition_score  = round(is_score / de * 100, 1) if de > 0 else 0.0

    return recipe
