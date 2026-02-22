import pytest
from unittest.mock import patch
from app.services.scraper import scrape_recipe_from_url

def test_scrape_recipe_success():
    """
    Test unitaire pour s'assurer que le service retourne le format correct attendu par le frontend.
    """
    mock_url = "https://example.com/recipe/1"
    
    # On simule le comportement de la librairie recipe_scrapers
    class MockScraper:
        def title(self): return "Gâteau au chocolat"
        def total_time(self): return 45
        def yields(self): return "4 servings"
        def ingredients(self): return ["200g chocolat", "3 oeufs", "100g sucre"]
        def instructions(self): return "Mélangez le tout.\nFaites cuire à 180°C pendant 30 min."
        def image(self): return "http://example.com/img.jpg"
        def nutrients(self): return {"calories": "450 kcal"}
        def host(self): return "example.com"
        
    with patch("app.services.scraper.scrape_me", return_value=MockScraper()):
        result = scrape_recipe_from_url(mock_url)
        
        assert result["title"] == "Gâteau au chocolat"
        assert result["total_time"] == 45
        assert len(result["ingredients"]) == 3
        assert "Mélangez le tout." in result["instructions"]

def test_scrape_recipe_failure():
    """
    Test unitaire pour s'assurer qu'une erreur de la librairie lève bien une ValueError.
    """
    with patch("app.services.scraper.scrape_me", side_effect=Exception("Website not supported")):
        with pytest.raises(ValueError) as exc:
            scrape_recipe_from_url("https://bad-url.com")
        assert "Impossible d'extraire la recette de cette URL" in str(exc.value)
