from pydantic import BaseModel
from typing import List, Dict

class ShoppingListItem(BaseModel):
    food_id: int
    food_name: str
    total_quantity_g: float

class ShoppingListResponse(BaseModel):
    plan_id: int
    items: List[ShoppingListItem]

class AlternativeRecipe(BaseModel):
    recipe_id: int
    recipe_name: str
    match_score: float # Plus c'est proche de 100, mieux c'est
