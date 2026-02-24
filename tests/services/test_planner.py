import pytest
from app.services.planner import generate_weekly_plan, RecipeCandidate

def create_mock_candidates():
    candidates = []
    # On crée 20 recettes fictives avec des macros qui permettent d'atteindre 2000kcal/jour (666kcal/repas moy)
    for i in range(1, 21):
        name = f"Recipe {i}"
        kcal = 600.0 + (i * 10)  # De 610 à 800 kcal (Moy: ~700)
        prot = 40.0 + i          # De 41 à 60g (Moy: 50.5g -> 3 repas = 151g/j)
        fat = 20.0 + (i * 0.5)   # De 20.5 à 30g (Moy: ~25g -> 3 repas = 75g/j)
        carb = 60.0 + (i * 2)    # De 62 à 100g (Moy: 81g -> 3 repas = 243g/j)
        is_score = 100.0 + (i * 5) # Recipe 20 est la plus rassasiante
        candidates.append(RecipeCandidate(i, name, kcal, prot, fat, carb, is_score))
    return candidates

def test_generate_weekly_plan_success():
    candidates = create_mock_candidates()
    
    # 2000 kcal ciblé
    target_kcal = 2000.0
    target_prot = 150.0
    target_fat = 60.0
    target_carb = 215.0
    
    result = generate_weekly_plan(
        candidates, target_kcal, target_prot, target_fat, target_carb,
        meals_per_day=3, days=7, tolerance=0.15
    )
    
    print(f"\nSOLVER MESSAGE: {result.message}")
    assert result.success is True
    assert len(result.meals) == 7 # 7 jours
    
    for day, meals in result.meals.items():
        assert len(meals) == 3 # 3 repas par jour
        
    # Vérification des calories totales (+/- 15% de 2000 * 7 = 14000)
    # Min = 11900, Max = 16100
    assert 11900 <= result.total_kcal <= 16100

def test_generate_weekly_plan_fail_no_candidates():
    result = generate_weekly_plan([], 2000, 150, 60, 200)
    assert result.success is False
    assert result.total_kcal == 0.0

def test_generate_weekly_plan_fail_impossible_macros():
    candidates = create_mock_candidates() # Avg macros = 550 kcal / repas => * 21 = ~11500 kcal

    # On demande un target délirant pour que le solveur échoue
    target_kcal = 50000.0
    target_prot = 150.0

    result = generate_weekly_plan(
        candidates, target_kcal, target_prot, 60.0, 200.0,
        meals_per_day=3, days=7, tolerance=0.05
    )

    assert result.success is False


# --- Nouveaux tests ---

def test_generate_weekly_plan_two_meals_per_day():
    """Le solveur fonctionne avec 2 repas/jour (14 repas au total)."""
    candidates = create_mock_candidates()
    result = generate_weekly_plan(
        candidates, target_kcal=1400.0, target_prot=100.0,
        target_fat=50.0, target_carb=150.0,
        meals_per_day=2, days=7, tolerance=0.30
    )
    assert result.success is True
    assert len(result.meals) == 7
    for day, meals in result.meals.items():
        assert len(meals) == 2


def test_generate_weekly_plan_variety_constraint():
    """Aucune recette n'apparaît plus de 3 fois sur la semaine."""
    candidates = create_mock_candidates()
    result = generate_weekly_plan(
        candidates, target_kcal=2000.0, target_prot=150.0,
        target_fat=60.0, target_carb=215.0,
        meals_per_day=3, days=7, tolerance=0.15
    )
    assert result.success is True

    recipe_counts: dict = {}
    for day_meals in result.meals.values():
        for recipe in day_meals:
            recipe_counts[recipe.id] = recipe_counts.get(recipe.id, 0) + 1

    for recipe_id, count in recipe_counts.items():
        assert count <= 3, f"La recette {recipe_id} apparaît {count} fois (max 3)"


def test_generate_weekly_plan_single_candidate_fails():
    """Un seul candidat ne peut pas satisfaire la contrainte de variété (max 3 fois)
    pour 21 repas → le solveur doit échouer."""
    single = [RecipeCandidate(1, "Unique", 700.0, 50.0, 25.0, 80.0, 120.0)]
    # 7 jours * 3 repas = 21 slots, mais max 3 usages → infaisable
    result = generate_weekly_plan(
        single, target_kcal=2100.0, target_prot=150.0,
        target_fat=75.0, target_carb=240.0,
        meals_per_day=3, days=7, tolerance=0.15
    )
    assert result.success is False


def test_generate_weekly_plan_five_days():
    """Le solveur génère correctement un plan sur 5 jours (pas forcément 7)."""
    candidates = create_mock_candidates()
    result = generate_weekly_plan(
        candidates, target_kcal=2000.0, target_prot=150.0,
        target_fat=60.0, target_carb=215.0,
        meals_per_day=3, days=5, tolerance=0.20
    )
    assert result.success is True
    assert len(result.meals) == 5
    for day, meals in result.meals.items():
        assert len(meals) == 3
