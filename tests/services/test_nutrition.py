import pytest
from app.models.recipe import Recipe, RecipeIngredient
from app.models.food import Food
from app.services.nutrition import calculate_recipe_nutrition

def test_calculate_recipe_nutrition_simple(db_session):
    # Setup - Fake Food in DB
    food_potato = Food(
        name="Potato",
        energy_kcal=77.0,
        proteins_g=2.0,
        carbohydrates_g=17.0,
        fat_g=0.1,
        fiber_g=2.2,
        water_g=79.0,
        yield_factor=1.0 # Potatoes keep their weight when boiled
    )
    food_chicken = Food(
        name="Chicken Breast",
        energy_kcal=165.0,
        proteins_g=31.0,
        carbohydrates_g=0.0,
        fat_g=3.6,
        fiber_g=0.0,
        water_g=65.0,
        yield_factor=0.7 # Loses water when cooked
    )
    db_session.add(food_potato)
    db_session.add(food_chicken)
    db_session.commit()
    
    # Setup - Recipe targeting 200g Potato + 150g Chicken
    recipe = Recipe(name="Chicken and Potatoes")
    db_session.add(recipe)
    db_session.flush()
    
    ing1 = RecipeIngredient(recipe_id=recipe.id, food_id=food_potato.id, quantity_g=200.0)
    ing2 = RecipeIngredient(recipe_id=recipe.id, food_id=food_chicken.id, quantity_g=150.0)
    recipe.ingredients = [ing1, ing2]
    
    # Process
    calculated_recipe = calculate_recipe_nutrition(db_session, recipe)
    
    # Assertion
    # Potatoes (200g): Kcal=154, Prot=4, Water=158, Fiber=4.4, yield=200g
    # Chicken (150g): Kcal=247.5, Prot=46.5, Water=97.5, yield=105g (150*0.7)
    # Total Weight = 305g
    # Total Kcal = 401.5
    # Total Prot = 50.5
    # Total Water = 255.5
    # Total Fiber = 4.4
    
    # DE = 401.5 / 305 = 1.3164
    assert calculated_recipe.energy_density == 1.3164
    
    # IS = (50.5 * 1.5) + (4.4 * 2.5) + (255.5 * 0.5) - (1.3164 * 10)
    # = 75.75 + 11.0 + 127.75 - 13.164 = 201.336 (arrondi à 2 chiffres = 201.34)
    assert calculated_recipe.satiety_index == 201.34

def test_calculate_recipe_empty(db_session):
    recipe = Recipe(name="Empty")
    calculated = calculate_recipe_nutrition(db_session, recipe)
    assert calculated.energy_density == 0.0
    assert calculated.satiety_index == 0.0
