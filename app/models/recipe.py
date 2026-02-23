from sqlalchemy import Column, Integer, String, Float, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base

class RecipeType(str, enum.Enum):
    COMPLETE = "complete"      # Plat unique
    SIMPLE = "simple"          # Assemblage d'aliments bruts
    MIXED = "mixed"            # Partielle (sauce) + brute

class IngredientState(str, enum.Enum):
    RAW = "raw"                # Cru
    COOKED = "cooked"          # Cuit

class RecipeVisibility(str, enum.Enum):
    GLOBAL = "global"          # Accessibe à tous
    PRIVATE = "private"        # Confiné à l'utilisateur

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    type = Column(Enum(RecipeType), default=RecipeType.COMPLETE)
    visibility = Column(Enum(RecipeVisibility), default=RecipeVisibility.PRIVATE)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Null = system/global
    
    # Indicateurs pré-calculés (pour 1 portion standard ou 100g)
    energy_density = Column(Float, nullable=True) # DE: kcal / volume (g)
    satiety_index = Column(Float, nullable=True)  # IS calculé
    internal_nutrition_score = Column(Float, nullable=True) # Nutriscore interne

    # Relations
    author = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", foreign_keys="[RecipeIngredient.recipe_id]", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    
    # Soit un aliment brut, soit une sous-recette (ex: sauce)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=True)
    sub_recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    
    quantity_g = Column(Float, nullable=False) # Quantité utilisée dans la recette (pour la préparation standard)
    state = Column(Enum(IngredientState), default=IngredientState.RAW) # état (cru/cuit)

    # Données brutes (optionnelles) pour l'affichage UI
    raw_quantity = Column(Float, nullable=True)
    raw_unit = Column(String(50), nullable=True)

    # Portion nommée utilisée (optionnelle) — détermine quantity_g si renseignée
    # Ex: "1 moyen citron vert = 67g" → food_portion_id pointe vers cette portion
    food_portion_id = Column(Integer, ForeignKey("food_portions.id"), nullable=True)

    # Relations
    recipe = relationship("Recipe", foreign_keys=[recipe_id], back_populates="ingredients")
    food = relationship("Food")
    food_portion = relationship("FoodPortion")
    sub_recipe = relationship("Recipe", foreign_keys=[sub_recipe_id])
