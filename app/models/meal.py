from sqlalchemy import Column, Integer, String, Float, Enum, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    
    # Indicateurs globaux calculés pour la semaine
    target_kcal = Column(Float, nullable=False)
    achieved_kcal = Column(Float, default=0.0)
    target_volume_g = Column(Float, nullable=True) # Cible de volume global
    
    meals = relationship("Meal", back_populates="plan", cascade="all, delete-orphan")

class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False, index=True)

    date = Column(Date, nullable=False)
    type = Column(Enum(MealType), nullable=False)

    # Le repas contient soit une recette complète/assemblage, soit des ingrédients isolés
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True, index=True)
    
    # Si le solveur a dû ajuster certaines portions pour fitter dans les macros
    portion_factor = Column(Float, default=1.0) 
    target_volume_g = Column(Float, nullable=True) # Cible de volume par repas

    plan = relationship("MealPlan", back_populates="meals")
    recipe = relationship("Recipe")
