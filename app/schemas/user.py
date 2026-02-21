from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import Gender, ActivityLevel, Objective

# --- Préférences Utilisateur ---

class UserPreferencesBase(BaseModel):
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_lactose_free: bool = False
    
    override_protein_ratio: Optional[float] = None
    override_carb_ratio: Optional[float] = None
    override_fat_ratio: Optional[float] = None

class UserPreferencesCreate(UserPreferencesBase):
    pass

class UserPreferences(UserPreferencesBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

# --- Contraintes / Exclusions Alimentaires ---

class DietaryConstraintBase(BaseModel):
    food_id: int

class DietaryConstraintCreate(DietaryConstraintBase):
    pass

class DietaryConstraint(DietaryConstraintBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

# --- Utilisateur ---

class UserBase(BaseModel):
    email: EmailStr
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    gender: Optional[Gender] = None
    activity_level: ActivityLevel = ActivityLevel.SEDENTARY
    daily_meals_count: int = 3
    objective: Objective = Objective.MAINTENANCE

class UserCreate(UserBase):
    preferences: Optional[UserPreferencesCreate] = None

class UserUpdate(BaseModel):
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    gender: Optional[Gender] = None
    activity_level: Optional[ActivityLevel] = None
    daily_meals_count: Optional[int] = None
    objective: Optional[Objective] = None
    preferences: Optional[UserPreferencesCreate] = None

class User(UserBase):
    id: int
    preferences: Optional[UserPreferences] = None

    class Config:
        from_attributes = True

# --- Résultats du Métabolisme ---

class MetabolicProfile(BaseModel):
    bmr: float
    tdee: float
    target_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    
    protein_ratio: float
    fat_ratio: float
    carb_ratio: float
