import asyncio
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.base import Base
from app.models.recipe import Recipe, RecipeType, RecipeVisibility
from app.models.food import Food

def seed_database():
    db = SessionLocal()
    
    import json
    import os
    
    seed_file_path = os.path.join(os.path.dirname(__file__), 'app', 'db', 'seed_foods.json')
    if os.path.exists(seed_file_path):
        print("Seeding database with real core ingredients...")
        with open(seed_file_path, 'r', encoding='utf-8') as f:
            foods_data = json.load(f)
            
        for fd in foods_data:
            # Check if food already exists to avoid duplicates
            existing = db.query(Food).filter(Food.name == fd['name']).first()
            if not existing:
                db.add(Food(**fd))
        db.commit()
        print("Foods seeded.")
    else:
        print(f"Warning: {seed_file_path} not found.")
    
    # Check if we already have recipes
    current_count = db.query(Recipe).count()
    if current_count >= 150:
        print("Database already seeded with enough recipes.")
        db.close()
        return

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
