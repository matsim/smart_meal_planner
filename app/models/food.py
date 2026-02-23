from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base

class Food(Base):
    """
    Base de données d'aliments (type CIQUAL)
    """
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    # Micronutriments essentiels et Macronutriments (pour 100g)
    energy_kcal = Column(Float, nullable=False, default=0.0)
    proteins_g = Column(Float, nullable=False, default=0.0)
    carbohydrates_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    fiber_g = Column(Float, nullable=False, default=0.0)
    water_g = Column(Float, nullable=False, default=0.0)
    
    # --- Données de Conversion pour Ingrédients ---
    density = Column(Float, nullable=False, default=1.0)
    portion_weight_g = Column(Float, nullable=False, default=100.0)
    
    # tags
    is_vegan = Column(Boolean, default=True)
    is_vegetarian = Column(Boolean, default=True)
    is_gluten_free = Column(Boolean, default=True)
    is_lactose_free = Column(Boolean, default=True)

    # Densité calorique (Kcal / 100g)
    # L'hydratation post-cuisson pourra être gérée via un facteur de rendement
    yield_factor = Column(Float, default=1.0) # ex: riz cru -> cuit = 3.0
    
    # Indicateur si cet aliment a été auto-généré via scraping sans valeurs (0 kcal)
    is_draft = Column(Boolean, default=False)

    # Portions nommées (ex: "1 moyen" = 67g, "1 brin" = 2g)
    portions = relationship("FoodPortion", back_populates="food", cascade="all, delete-orphan", lazy="selectin")
