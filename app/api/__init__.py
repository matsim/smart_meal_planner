from fastapi import APIRouter
from app.api import users, foods, recipes, planner

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(foods.router, prefix="/foods", tags=["foods"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
