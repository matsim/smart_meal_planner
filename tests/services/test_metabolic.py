import pytest
from app.models.user import User, ActivityLevel, Gender, Objective, UserPreferences
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


# --- Nouveaux tests ---

def test_calculate_tdee_all_levels():
    """Vérifie les 5 niveaux d'activité."""
    bmr = 1000.0
    assert calculate_tdee(bmr, ActivityLevel.SEDENTARY)   == pytest.approx(1200.0)
    assert calculate_tdee(bmr, ActivityLevel.LIGHT)        == pytest.approx(1375.0)
    assert calculate_tdee(bmr, ActivityLevel.MODERATE)     == pytest.approx(1550.0)
    assert calculate_tdee(bmr, ActivityLevel.ACTIVE)       == pytest.approx(1725.0)
    assert calculate_tdee(bmr, ActivityLevel.VERY_ACTIVE)  == pytest.approx(1900.0)


def test_calculate_metabolic_profile_maintenance():
    """Objectif maintenance : pas d'ajustement calorique."""
    user = User(
        age=30, weight_kg=70.0, height_cm=175.0, gender=Gender.MALE,
        activity_level=ActivityLevel.MODERATE, objective=Objective.MAINTENANCE
    )
    # BMR = 10*70 + 6.25*175 - 5*30 + 5 = 700 + 1093.75 - 150 + 5 = 1648.75
    # TDEE = 1648.75 * 1.55 = 2555.5625  → arrondi 2555.56
    # MAINTENANCE = +0  →  target = 2555.56
    profile = calculate_metabolic_profile(user)
    assert profile.bmr == 1648.75
    assert profile.tdee == pytest.approx(2555.56, abs=0.1)
    assert profile.target_kcal == pytest.approx(2555.56, abs=0.1)
    # Ratios par défaut MAINTENANCE : P:25%, F:30%, C:45%
    assert profile.protein_ratio == 0.25
    assert profile.fat_ratio     == 0.30
    assert profile.carb_ratio    == 0.45


def test_calculate_metabolic_profile_muscle_gain():
    """Objectif prise de masse : +300 kcal sur le TDEE."""
    user = User(
        age=25, weight_kg=75.0, height_cm=178.0, gender=Gender.MALE,
        activity_level=ActivityLevel.ACTIVE, objective=Objective.MUSCLE_GAIN
    )
    # BMR = 10*75 + 6.25*178 - 5*25 + 5 = 750 + 1112.5 - 125 + 5 = 1742.5
    # TDEE = 1742.5 * 1.725 = 3005.8125  → arrondi 3005.81
    # MUSCLE_GAIN = +300  →  target ≈ 3305.81
    profile = calculate_metabolic_profile(user)
    assert profile.bmr   == 1742.5
    assert profile.tdee  == pytest.approx(3005.81, abs=0.1)
    assert profile.target_kcal == pytest.approx(3305.81, abs=0.1)
    # Ratios par défaut MUSCLE_GAIN : P:30%, F:25%, C:45%
    assert profile.protein_ratio == 0.30
    assert profile.fat_ratio     == 0.25
    assert profile.carb_ratio    == 0.45


def test_calculate_bmr_missing_data_returns_zero():
    """Le BMR vaut 0 si une donnée physiologique manque."""
    # age manquant
    user_no_age = User(weight_kg=80.0, height_cm=180.0, gender=Gender.MALE)
    assert calculate_bmr(user_no_age) == 0.0

    # poids manquant
    user_no_weight = User(age=30, height_cm=180.0, gender=Gender.MALE)
    assert calculate_bmr(user_no_weight) == 0.0

    # taille manquante
    user_no_height = User(age=30, weight_kg=80.0, gender=Gender.MALE)
    assert calculate_bmr(user_no_height) == 0.0

    # genre manquant
    user_no_gender = User(age=30, weight_kg=80.0, height_cm=180.0)
    assert calculate_bmr(user_no_gender) == 0.0


def test_calculate_metabolic_profile_incomplete_returns_zeros():
    """Si le BMR est 0 (données manquantes), tout le profil vaut 0."""
    user = User(
        weight_kg=80.0, height_cm=180.0, gender=Gender.MALE,
        activity_level=ActivityLevel.MODERATE, objective=Objective.MAINTENANCE
    )  # age manquant → BMR = 0
    profile = calculate_metabolic_profile(user)
    assert profile.bmr         == 0.0
    assert profile.tdee        == 0.0
    assert profile.target_kcal == 0.0
    assert profile.protein_g   == 0.0


def test_calculate_metabolic_profile_preference_overrides():
    """Les surcharges de macros dans les préférences remplacent les valeurs par défaut."""
    user = User(
        age=30, weight_kg=80.0, height_cm=180.0, gender=Gender.MALE,
        activity_level=ActivityLevel.SEDENTARY, objective=Objective.WEIGHT_LOSS
    )
    # Surcharger les ratios : P=50%, F=30%, C=20% → total 1.0, normalisation sans effet
    user.preferences = UserPreferences(
        override_protein_ratio=0.5,
        override_fat_ratio=0.3,
        override_carb_ratio=0.2
    )
    profile = calculate_metabolic_profile(user)
    assert profile.protein_ratio == pytest.approx(0.5, abs=0.001)
    assert profile.fat_ratio     == pytest.approx(0.3, abs=0.001)
    assert profile.carb_ratio    == pytest.approx(0.2, abs=0.001)


def test_calculate_metabolic_profile_preference_overrides_normalized():
    """Les surcharges dont la somme != 1 sont normalisées."""
    user = User(
        age=30, weight_kg=80.0, height_cm=180.0, gender=Gender.MALE,
        activity_level=ActivityLevel.SEDENTARY, objective=Objective.MAINTENANCE
    )
    # Ratios volontairement non-normalisés : 2, 1, 1 → somme = 4 → après normalisation : 0.5, 0.25, 0.25
    user.preferences = UserPreferences(
        override_protein_ratio=2.0,
        override_fat_ratio=1.0,
        override_carb_ratio=1.0
    )
    profile = calculate_metabolic_profile(user)
    assert profile.protein_ratio == pytest.approx(0.5,  abs=0.001)
    assert profile.fat_ratio     == pytest.approx(0.25, abs=0.001)
    assert profile.carb_ratio    == pytest.approx(0.25, abs=0.001)
    # La somme doit toujours faire 1
    total = profile.protein_ratio + profile.fat_ratio + profile.carb_ratio
    assert total == pytest.approx(1.0, abs=0.001)
