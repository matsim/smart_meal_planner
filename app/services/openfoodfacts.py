import httpx
import logging

logger = logging.getLogger(__name__)

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

def search_food_off(query: str) -> dict | None:
    """
    Recherche un aliment sur OpenFoodFacts à partir d'une chaîne de texte.
    Retourne un dictionnaire avec les macros si un produit pertinent est trouvé, sinon None.
    """
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 3,
        "fields": "product_name,nutriments,categories_tags",
        "sort_by": "unique_scans_n" # Trier par popularité pour avoir le vrai produit de base
    }
    
    headers = {
        "User-Agent": "SmartMealPlanner - Dev Project - https://github.com/votre_repo"
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(OFF_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "products" in data and len(data["products"]) > 0:
                # On prend le premier produit pertinent qui contient des nutriments exploitables
                for product in data["products"]:
                    nutriments = product.get("nutriments", {})
                    if "energy-kcal_100g" in nutriments:
                        return {
                            "name": product.get("product_name", query),
                            "energy_kcal": float(nutriments.get("energy-kcal_100g", 0)),
                            "proteins_g": float(nutriments.get("proteins_100g", 0)),
                            "fat_g": float(nutriments.get("fat_100g", 0)),
                            "carbohydrates_g": float(nutriments.get("carbohydrates_100g", 0)),
                            "fiber_g": float(nutriments.get("fiber_100g", 0)),
                            "water_g": 0.0, # OPENFOODFACTS ne renvoie pas souvent le taux d'humidité
                            "off_match": True
                        }
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la recherche OpenFoodFacts pour '{query}': {e}")
        return None

def search_many_food_off(query: str, limit: int = 5) -> list[dict]:
    """
    Recherche plusieurs aliments sur OpenFoodFacts à partir d'une chaîne de texte.
    Retourne une liste de dictionnaires pour permettre à l'utilisateur de choisir.
    """
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": max(limit, 5),
        "fields": "product_name,nutriments,categories_tags",
        "sort_by": "unique_scans_n"
    }
    
    headers = {
        "User-Agent": "SmartMealPlanner - Dev Project - https://github.com/votre_repo"
    }

    results = []
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(OFF_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "products" in data:
                for product in data["products"]:
                    nutriments = product.get("nutriments", {})
                    name = product.get("product_name", "").strip()
                    if name and "energy-kcal_100g" in nutriments:
                        results.append({
                            "name": name,
                            "energy_kcal": float(nutriments.get("energy-kcal_100g", 0)),
                            "proteins_g": float(nutriments.get("proteins_100g", 0)),
                            "fat_g": float(nutriments.get("fat_100g", 0)),
                            "carbohydrates_g": float(nutriments.get("carbohydrates_100g", 0)),
                            "fiber_g": float(nutriments.get("fiber_100g", 0)),
                            "water_g": 0.0,
                            "off_match": True
                        })
                        if len(results) >= limit:
                            break
    except Exception as e:
        logger.error(f"Erreur OFF multiple pour '{query}': {e}")
    
    # Deduplicate by name
    seen = set()
    unique_results = []
    for r in results:
        if r["name"].lower() not in seen:
            seen.add(r["name"].lower())
            unique_results.append(r)
    
    return unique_results
