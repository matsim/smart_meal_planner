from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.food import Food as FoodModel
from app.models.food_portion import FoodPortion as FoodPortionModel
from app.schemas.food_portion import FoodPortion, FoodPortionCreate

router = APIRouter()


@router.get("/{food_id}/portions", response_model=List[FoodPortion])
def list_portions(food_id: int, db: Session = Depends(get_db)) -> Any:
    """Lister toutes les portions nommées d'un aliment."""
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Aliment non trouvé")
    return food.portions


@router.post("/{food_id}/portions", response_model=FoodPortion, status_code=201)
def create_portion(food_id: int, portion_in: FoodPortionCreate, db: Session = Depends(get_db)) -> Any:
    """Créer une nouvelle portion nommée pour un aliment."""
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Aliment non trouvé")

    # Si is_default=True, désactiver les autres défauts
    if portion_in.is_default:
        db.query(FoodPortionModel).filter(
            FoodPortionModel.food_id == food_id,
            FoodPortionModel.is_default == True  # noqa: E712
        ).update({"is_default": False})

    db_portion = FoodPortionModel(food_id=food_id, **portion_in.model_dump())
    db.add(db_portion)
    db.commit()
    db.refresh(db_portion)
    return db_portion


@router.put("/{food_id}/portions/{portion_id}", response_model=FoodPortion)
def update_portion(food_id: int, portion_id: int, portion_in: FoodPortionCreate, db: Session = Depends(get_db)) -> Any:
    """Modifier une portion existante."""
    portion = db.query(FoodPortionModel).filter(
        FoodPortionModel.id == portion_id,
        FoodPortionModel.food_id == food_id
    ).first()
    if not portion:
        raise HTTPException(status_code=404, detail="Portion non trouvée")

    if portion_in.is_default:
        db.query(FoodPortionModel).filter(
            FoodPortionModel.food_id == food_id,
            FoodPortionModel.is_default == True  # noqa: E712
        ).update({"is_default": False})

    for field, val in portion_in.model_dump().items():
        setattr(portion, field, val)
    db.commit()
    db.refresh(portion)
    return portion


@router.delete("/{food_id}/portions/{portion_id}", status_code=204)
def delete_portion(food_id: int, portion_id: int, db: Session = Depends(get_db)) -> None:
    """Supprimer une portion."""
    portion = db.query(FoodPortionModel).filter(
        FoodPortionModel.id == portion_id,
        FoodPortionModel.food_id == food_id
    ).first()
    if not portion:
        raise HTTPException(status_code=404, detail="Portion non trouvée")
    db.delete(portion)
    db.commit()
