from pydantic import BaseModel
from typing import Optional, List

class FoodBase(BaseModel):
    name: str
    energy_kcal: float
    proteins_g: float
    carbohydrates_g: float
    fat_g: float
    fiber_g: float
    water_g: float
    
    density: float = 1.0
    portion_weight_g: float = 100.0
    
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
    portions: List['FoodPortion'] = []

    class Config:
        from_attributes = True

# Import ici pour éviter les imports circulaires
from app.schemas.food_portion import FoodPortion  # noqa: E402
Food.model_rebuild()

class FoodMergeRequest(BaseModel):
    target_id: int
    source_ids: list[int]
