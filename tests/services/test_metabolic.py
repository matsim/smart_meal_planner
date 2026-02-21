from app.models.user import User, ActivityLevel, Gender, Objective
from app.services.metabolic import calculate_bmr, calculate_tdee, calculate_metabolic_profile

def test_calculate_bmr_male():
    user = User(
        age=30,
        weight_kg=80.0,
        height_cm=180.0,
        gender=Gender.MALE
    )
    # Mifflin-St Jeor: 10 * 80 + 6.25 * 180 - 5 * 30 + 5
    # = 800 + 1125 - 150 + 5 = 1925 - 150 + 5 = 1780
    bmr = calculate_bmr(user)
    assert bmr == 1780.0

def test_calculate_bmr_female():
    user = User(
        age=25,
        weight_kg=60.0,
        height_cm=165.0,
        gender=Gender.FEMALE
    )
    # Mifflin-St Jeor: 10 * 60 + 6.25 * 165 - 5 * 25 - 161
    # = 600 + 1031.25 - 125 - 161 = 1345.25
    bmr = calculate_bmr(user)
    assert bmr == 1345.25

def test_calculate_tdee():
    bmr = 1500.0
    # SEDENTARY = 1.2
    tdee = calculate_tdee(bmr, ActivityLevel.SEDENTARY)
    assert tdee == 1800.0
    
    # MODERATE = 1.55
    tdee = calculate_tdee(bmr, ActivityLevel.MODERATE)
    assert tdee == 2325.0

def test_calculate_metabolic_profile_weight_loss():
    user = User(
        age=30,
        weight_kg=80.0,
        height_cm=180.0,
        gender=Gender.MALE,
        activity_level=ActivityLevel.SEDENTARY,
        objective=Objective.WEIGHT_LOSS
    )
    # BMR = 1780.0
    # TDEE = 1780.0 * 1.2 = 2136.0
    # WEIGHT_LOSS = -500 kcal
    # Target Kcal = 1636.0
    
    # Safety Check : 1780.0 * 0.9 = 1602.0 (La cible est au dessus du plancher sécurité) -> ok
    
    profile = calculate_metabolic_profile(user)
    
    assert profile.bmr == 1780.0
    assert profile.tdee == 2136.0
    assert profile.target_kcal == 1636.0
    
    # Macros défault Weight Loss: (P:35, F:35, C:30)
    assert profile.protein_ratio == 0.35
    assert profile.fat_ratio == 0.35
    assert profile.carb_ratio == 0.30

def test_calculate_metabolic_profile_safety_floor():
    user = User(
        age=25,
        weight_kg=50.0, # très léger
        height_cm=160.0,
        gender=Gender.FEMALE,
        activity_level=ActivityLevel.SEDENTARY,
        objective=Objective.WEIGHT_LOSS
    )
    # BMR = 10 * 50 + 6.25 * 160 - 5 * 25 - 161 = 500 + 1000 - 125 - 161 = 1214
    # TDEE = 1214 * 1.2 = 1456.8
    # Objectif perte de poids: 1456.8 - 500 = 956.8 kcal
    # Plancher sécurité: 1214 * 0.9 = 1092.6
    # La fonction doit retourner le max des deux, donc le plancher de sécurité.
    
    profile = calculate_metabolic_profile(user)
    assert profile.target_kcal == 1092.6
    assert profile.bmr == 1214.0
