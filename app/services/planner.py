import pulp
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import datetime

# --- Types Bâtards pour le Solveur ---

class RecipeCandidate:
    """Structure légère représentant une recette pour le solveur"""
    def __init__(self, id: int, name: str, kcal: float, prot: float, fat: float, carb: float, is_score: float):
        self.id = id
        self.name = name
        self.kcal = kcal
        self.prot = prot
        self.fat = fat
        self.carb = carb
        self.is_score = is_score

class WeeklyPlanResult:
    def __init__(self, success: bool, meals: Dict[str, List[RecipeCandidate]], total_kcal: float, msg: str):
        self.success = success
        self.meals = meals # dict par jour ex: 'Day_1': [R1, R2, R3]
        self.total_kcal = total_kcal
        self.message = msg

def generate_weekly_plan(
    candidates: List[RecipeCandidate], 
    target_kcal: float, 
    target_prot: float, 
    target_fat: float, 
    target_carb: float,
    meals_per_day: int = 3,
    days: int = 7,
    tolerance: float = 0.15
) -> WeeklyPlanResult:
    """
    Solveur PuLP (Mixed-Integer Linear Programming) pour générer une semaine de repas.
    Objectif : Maximiser la Satiété (Satiety Index)
    Contraintes : Respecter Kcal et Macros (+/- 15%) sur la semaine.
    """
    if not candidates:
        return WeeklyPlanResult(False, {}, 0.0, "Aucune recette candidate fournie.")

    # 1. Initialiser le Problème
    prob = pulp.LpProblem("Smart_Meal_Planner_Weekly", pulp.LpMaximize)

    # 2. Créer les Variables de Décision
    # x[d][m][r] = 1 si la recette `r` est mangée le jour `d` au repas `m`
    # On utilise des Booléens (0 ou 1)
    
    x = {}
    for d in range(1, days + 1):
        x[d] = {}
        for m in range(1, meals_per_day + 1):
            x[d][m] = {}
            for r in candidates:
                # Nom de variable unique
                var_name = f"day_{d}_meal_{m}_recipe_{r.id}"
                x[d][m][r.id] = pulp.LpVariable(var_name, cat="Binary")

    # 3. Fonction Objectif : Maximiser la satiété totale sur la semaine
    # Somme (x * r.is_score) pour tous les repas
    objective = pulp.lpSum(
        x[d][m][r.id] * r.is_score
        for d in range(1, days + 1)
        for m in range(1, meals_per_day + 1)
        for r in candidates
    )
    prob += objective

    # 4. Contraintes Structurelles (Un seul choix de recette par repas)
    for d in range(1, days + 1):
        for m in range(1, meals_per_day + 1):
            prob += pulp.lpSum(x[d][m][r.id] for r in candidates) == 1, f"One_recipe_per_meal_D{d}_M{m}"

    # 5. Contraintes Nutritionnelles (Sur la semaine)
    weekly_kcal_min = (target_kcal * days) * (1 - tolerance)
    weekly_kcal_max = (target_kcal * days) * (1 + tolerance)
    
    weekly_prot_min = (target_prot * days) * (1 - tolerance)
    weekly_prot_max = (target_prot * days) * (1 + tolerance)
    
    weekly_fat_min = (target_fat * days) * (1 - tolerance)
    weekly_fat_max = (target_fat * days) * (1 + tolerance)
    
    weekly_carb_min = (target_carb * days) * (1 - tolerance)
    weekly_carb_max = (target_carb * days) * (1 + tolerance)

    # Variables d'accumulation hebdomadaire
    total_kcal_expr = pulp.lpSum(x[d][m][r.id] * r.kcal for d in range(1, days+1) for m in range(1, meals_per_day+1) for r in candidates)
    total_prot_expr = pulp.lpSum(x[d][m][r.id] * r.prot for d in range(1, days+1) for m in range(1, meals_per_day+1) for r in candidates)
    total_fat_expr  = pulp.lpSum(x[d][m][r.id] * r.fat  for d in range(1, days+1) for m in range(1, meals_per_day+1) for r in candidates)
    total_carb_expr = pulp.lpSum(x[d][m][r.id] * r.carb for d in range(1, days+1) for m in range(1, meals_per_day+1) for r in candidates)

    prob += total_kcal_expr >= weekly_kcal_min, "Min_Weekly_Kcal"
    prob += total_kcal_expr <= weekly_kcal_max, "Max_Weekly_Kcal"
    
    prob += total_prot_expr >= weekly_prot_min, "Min_Weekly_Prot"
    prob += total_prot_expr <= weekly_prot_max, "Max_Weekly_Prot"
    
    prob += total_fat_expr >= weekly_fat_min, "Min_Weekly_Fat"
    prob += total_fat_expr <= weekly_fat_max, "Max_Weekly_Fat"

    prob += total_carb_expr >= weekly_carb_min, "Min_Weekly_Carb"
    prob += total_carb_expr <= weekly_carb_max, "Max_Weekly_Carb"

    # 6. Variété : Éviter de manger la même recette plus de 3 fois par semaine (Arbitraire pour le test)
    for r in candidates:
         prob += pulp.lpSum(x[d][m][r.id] for d in range(1, days+1) for m in range(1, meals_per_day+1)) <= 3, f"Variety_Limit_{r.id}"

    # 7. Résolution
    # Pour PuLP par défaut, utilise CBC (Coin-or branch and cut)
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))

    # 8. Traitement du Résultat
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return WeeklyPlanResult(False, {}, 0.0, f"Échec de la résolution (Statut: {status}). Essayez d'élargir la tolérance croisée ou d'ajouter plus de recettes.")

    # Reconstruction du planning
    plan_dict = defaultdict(list)
    achieved_kcal = 0.0
    
    for d in range(1, days + 1):
        day_key = f"Day_{d}"
        for m in range(1, meals_per_day + 1):
            for r in candidates:
                # Si la variable vaut 1.0 (ou très proche à cause des flottants)
                if pulp.value(x[d][m][r.id]) == 1.0:
                    plan_dict[day_key].append(r)
                    achieved_kcal += r.kcal

    return WeeklyPlanResult(True, dict(plan_dict), achieved_kcal, "Plan généré avec succès.")
