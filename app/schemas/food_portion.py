from pydantic import BaseModel
from typing import Optional


class FoodPortionBase(BaseModel):
    name: str          # ex: "1 moyen", "1 brin", "1 tasse"
    weight_g: float    # poids en grammes de cette portion
    is_default: bool = False


class FoodPortionCreate(FoodPortionBase):
    pass


class FoodPortion(FoodPortionBase):
    id: int
    food_id: int

    class Config:
        from_attributes = True
