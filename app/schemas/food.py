from pydantic import BaseModel
from typing import Optional

class FoodBase(BaseModel):
    name: str
    energy_kcal: float
    proteins_g: float
    carbohydrates_g: float
    fat_g: float
    fiber_g: float
    water_g: float
    
    is_vegan: bool = True
    is_vegetarian: bool = True
    is_gluten_free: bool = True
    is_lactose_free: bool = True
    
    yield_factor: float = 1.0
    is_draft: bool = False

class FoodCreate(FoodBase):
    pass

class Food(FoodBase):
    id: int

    class Config:
        from_attributes = True
