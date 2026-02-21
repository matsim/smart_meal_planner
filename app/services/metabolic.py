from app.models.user import User, Gender, ActivityLevel, Objective
from app.schemas.user import MetabolicProfile

ACTIVITY_MULTIPLIERS = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}

OBJECTIVE_ADJUSTMENTS = {
    Objective.WEIGHT_LOSS: -500,
    Objective.MAINTENANCE: 0,
    Objective.MUSCLE_GAIN: 300,
}

# Ratios par défaut (Protéines, Lipides, Glucides) basé sur l'objectif
DEFAULT_MACROS = {
    Objective.WEIGHT_LOSS: (0.35, 0.35, 0.30),
    Objective.MAINTENANCE: (0.25, 0.30, 0.45),
    Objective.MUSCLE_GAIN: (0.30, 0.25, 0.45),
}

def calculate_bmr(user: User) -> float:
    """Calcul du métabolisme de base (Mifflin-St Jeor)"""
    if not all([user.weight_kg, user.height_cm, user.age, user.gender]):
        return 0.0 # Données manquantes
    
    base = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age
    if user.gender == Gender.MALE:
        return base + 5
    else:
        return base - 161

def calculate_tdee(bmr: float, activity_level: ActivityLevel) -> float:
    """Total Daily Energy Expenditure"""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier

def calculate_metabolic_profile(user: User) -> MetabolicProfile:
    bmr = calculate_bmr(user)
    tdee = calculate_tdee(bmr, user.activity_level)
    
    if bmr == 0.0:
        return MetabolicProfile(
            bmr=0.0, tdee=0.0, target_kcal=0.0,
            protein_g=0.0, fat_g=0.0, carbs_g=0.0,
            protein_ratio=0.0, fat_ratio=0.0, carb_ratio=0.0
        )
    
    # Kcal Cible
    adjustment = OBJECTIVE_ADJUSTMENTS.get(user.objective, 0)
    target_kcal = tdee + adjustment
    # Ne jamais descendre sous le BMR - 10% (sécurité)
    target_kcal = max(target_kcal, bmr * 0.9)
    
    # Ratios (on prend les surcharges si elles existent)
    p_ratio, f_ratio, c_ratio = DEFAULT_MACROS[user.objective]
    
    if user.preferences:
        p_ratio = user.preferences.override_protein_ratio or p_ratio
        f_ratio = user.preferences.override_fat_ratio or f_ratio
        c_ratio = user.preferences.override_carb_ratio or c_ratio
        
        # S'assurer que le total fait environ 1.0 (on normalise au cas où)
        total_ratio = p_ratio + f_ratio + c_ratio
        if total_ratio > 0:
            p_ratio /= total_ratio
            f_ratio /= total_ratio
            c_ratio /= total_ratio
            
    # Calcul en grammes (1g Prot = 4Kcal, 1g Lip = 9Kcal, 1g Glu = 4Kcal)
    protein_g = (target_kcal * p_ratio) / 4.0
    fat_g = (target_kcal * f_ratio) / 9.0
    carbs_g = (target_kcal * c_ratio) / 4.0
    
    return MetabolicProfile(
        bmr=round(bmr, 2),
        tdee=round(tdee, 2),
        target_kcal=round(target_kcal, 2),
        protein_g=round(protein_g, 2),
        fat_g=round(fat_g, 2),
        carbs_g=round(carbs_g, 2),
        protein_ratio=round(p_ratio, 3),
        fat_ratio=round(f_ratio, 3),
        carb_ratio=round(c_ratio, 3)
    )
