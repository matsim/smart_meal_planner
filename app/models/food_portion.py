from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class FoodPortion(Base):
    """
    Portion nommée pour un aliment.
    Ex : Citron vert → "1 moyen" = 67g, "1 petit" = 44g, "1 c.à.s jus" = 15g

    Permet de convertir les quantités en pièces/unités vers des grammes
    pour le calcul des macronutriments.
    """
    __tablename__ = "food_portions"

    id = Column(Integer, primary_key=True, index=True)

    # Relation vers l'aliment
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False, index=True)

    # Label de la portion tel qu'affiché à l'utilisateur
    # Exemples : "1 moyen", "1 petit", "1 grand", "1 brin", "1 tasse", "1 c.à.s"
    name = Column(String, nullable=False)

    # Poids en grammes de cette portion
    weight_g = Column(Float, nullable=False)

    # Portion par défaut suggérée pour cet aliment
    is_default = Column(Boolean, default=False, nullable=False)

    # Relation inverse
    food = relationship("Food", back_populates="portions")
