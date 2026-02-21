import asyncio
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.base import Base
from app.models.recipe import Recipe, RecipeType, RecipeVisibility
from app.models.food import Food

def seed_database():
    db = SessionLocal()
    
    # Check if we already have recipes
    current_count = db.query(Recipe).count()
    if current_count >= 150:
        print("Database already seeded with enough recipes.")
        db.close()
        return

    print("Seeding database with demo foods and recipes...")

    # Create some basic foods
    # (Just some dummy data to avoid emptiness, in a real app this would be CIQUAL)
    foods_data = [
        {"name": "Poulet", "energy_kcal": 165, "proteins_g": 31, "fat_g": 3.6, "carbohydrates_g": 0},
        {"name": "Riz", "energy_kcal": 130, "proteins_g": 2.7, "fat_g": 0.3, "carbohydrates_g": 28},
        {"name": "Brocoli", "energy_kcal": 34, "proteins_g": 2.8, "fat_g": 0.4, "carbohydrates_g": 7},
        {"name": "Saumon", "energy_kcal": 208, "proteins_g": 20, "fat_g": 13, "carbohydrates_g": 0},
        {"name": "Pâtes", "energy_kcal": 131, "proteins_g": 5, "fat_g": 1, "carbohydrates_g": 25},
        {"name": "Bifteck", "energy_kcal": 250, "proteins_g": 26, "fat_g": 15, "carbohydrates_g": 0},
        {"name": "Pomme de terre", "energy_kcal": 77, "proteins_g": 2, "fat_g": 0.1, "carbohydrates_g": 17},
        {"name": "Œuf", "energy_kcal": 155, "proteins_g": 13, "fat_g": 11, "carbohydrates_g": 1.1},
    ]

    for fd in foods_data:
        db.add(Food(**fd))
    
    db.commit()

    # Create 150 recipe stubs with varied nutritional mock scores 
    # to feed the PuLP linear programming algorithm
    for i in range(current_count + 1, 151):
        recipe = Recipe(
            name=f"Plat équilibré #{i}",
            description="Recette générée par le seeder",
            type=RecipeType.COMPLETE,
            visibility=RecipeVisibility.GLOBAL,
            # We mock the scores so the algorithm has things to optimize
            energy_density=round(1.0 + (i * 0.05), 2),
            satiety_index=round(100.0 + (i * 2), 2),
            internal_nutrition_score=round(10.0 - (i * 0.2), 2)
        )
        db.add(recipe)
        
    db.commit()
    print(f"Added {db.query(Recipe).count()} recipes. The algorithm can now plan weeks.")
    db.close()

if __name__ == "__main__":
    seed_database()
