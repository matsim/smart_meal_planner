from pydantic import BaseModel
from typing import Optional, List
from app.models.recipe import RecipeType, RecipeVisibility
from app.schemas.food import Food

class RecipeIngredientBase(BaseModel):
    quantity_g: float

class RecipeIngredientCreateFood(RecipeIngredientBase):
    food_id: int

class RecipeIngredientCreateSubRecipe(RecipeIngredientBase):
    sub_recipe_id: int

class RecipeIngredient(RecipeIngredientBase):
    id: int
    recipe_id: int
    food: Optional[Food] = None
    sub_recipe_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Recipe ---
        
class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: RecipeType = RecipeType.COMPLETE
    visibility: RecipeVisibility = RecipeVisibility.PRIVATE

class RecipeCreate(RecipeBase):
    author_id: Optional[int] = None
    ingredients_food: Optional[List[RecipeIngredientCreateFood]] = []
    ingredients_sub: Optional[List[RecipeIngredientCreateSubRecipe]] = []

class Recipe(RecipeBase):
    id: int
    author_id: Optional[int] = None
    energy_density: Optional[float] = None
    satiety_index: Optional[float] = None
    internal_nutrition_score: Optional[float] = None
    
    ingredients: List[RecipeIngredient] = []

    class Config:
        from_attributes = True
