from pydantic import BaseModel
from typing import Optional, List
from app.models.recipe import RecipeType, RecipeVisibility
from app.schemas.food import Food

class RecipeIngredientBase(BaseModel):
    quantity_g: float
    raw_quantity: Optional[float] = None
    raw_unit: Optional[str] = None

class RecipeIngredientCreateFood(RecipeIngredientBase):
    food_id: int
    food_portion_id: Optional[int] = None

class RecipeIngredientCreateSubRecipe(RecipeIngredientBase):
    sub_recipe_id: int

class RecipeIngredient(RecipeIngredientBase):
    id: int
    recipe_id: int
    food: Optional[Food] = None
    sub_recipe_id: Optional[int] = None
    food_portion_id: Optional[int] = None

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
    total_weight_g: Optional[float] = None
    proteins_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    is_vegetarian: bool = True
    is_vegan: bool = True
    is_gluten_free: bool = True
    is_lactose_free: bool = True

    ingredients: List[RecipeIngredient] = []

    class Config:
        from_attributes = True
