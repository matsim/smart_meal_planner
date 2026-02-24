from sqlalchemy import Column, Integer, String, Float, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base

class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"
    
class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"

class Objective(str, enum.Enum):
    WEIGHT_LOSS = "weight_loss"
    MAINTENANCE = "maintenance"
    MUSCLE_GAIN = "muscle_gain"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # Données physiologiques
    age = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    activity_level = Column(Enum(ActivityLevel), default=ActivityLevel.SEDENTARY)
    
    # Paramètres de planification
    daily_meals_count = Column(Integer, default=3)
    objective = Column(Enum(Objective), default=Objective.MAINTENANCE)
    target_weekly_kcal = Column(Float, nullable=True) # cible_kcal_hebdo
    
    # Relations
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    recipes = relationship("Recipe", back_populates="author")
    constraints = relationship("DietaryConstraint", back_populates="user")

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Diététique (simplifié pour l'instant)
    is_vegetarian = Column(Boolean, default=False)
    is_vegan = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_lactose_free = Column(Boolean, default=False)
    
    # Surcharge des macros (null = calcul automatique)
    override_protein_ratio = Column(Float, nullable=True)
    override_carb_ratio = Column(Float, nullable=True)
    override_fat_ratio = Column(Float, nullable=True)

    user = relationship("User", back_populates="preferences")

class DietaryConstraint(Base):
    __tablename__ = "dietary_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=True, index=True)  # ID of specific food to exclude
    
    user = relationship("User", back_populates="constraints")
