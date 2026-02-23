from typing import Optional, Dict, Any
from recipe_scrapers import scrape_me
from pydantic import HttpUrl
from app.services.ingredient_parser import parse_ingredient

def scrape_recipe_from_url(url: str) -> Dict[str, Any]:
    """
    Extrait les données d'une recette depuis une URL via les métadonnées schema.org/Recipe.
    Utilise la lib 'recipe-scrapers'.
    """
    try:
        scraper = scrape_me(url, wild_mode=True)
        
        # Récupération et parsing des ingrédients
        raw_ingredients = scraper.ingredients()
        parsed_ingredients = [parse_ingredient(ing) for ing in raw_ingredients]
        
        return {
            "title": scraper.title(),
            "total_time": scraper.total_time(),
            "yields": scraper.yields(),
            "ingredients": parsed_ingredients,  # <- Modification clé : liste d'objets (raw, qty, unit, product)
            "instructions": scraper.instructions(),
            "image": scraper.image(),
            "nutrients": scraper.nutrients(),
            "host": scraper.host()
        }
    except Exception as e:
        raise ValueError(f"Impossible d'extraire la recette de cette URL : {str(e)}")
