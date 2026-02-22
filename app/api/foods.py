from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.food import Food as FoodModel
from app.schemas.food import Food, FoodCreate

router = APIRouter()

@router.post("/", response_model=Food)
def create_food(
    *,
    db: Session = Depends(get_db),
    food_in: FoodCreate,
) -> Any:
    """
    Ajouter un nouvel aliment à la base (ex: depuis Ciqual).
    """
    db_obj = FoodModel(**food_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[Food])
def list_foods(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None
) -> Any:
    """
    Lister les aliments avec recherche optionnelle par nom.
    """
    query = db.query(FoodModel)
    if search:
        query = query.filter(FoodModel.name.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()

@router.get("/{food_id}", response_model=Food)
def read_food(
    *,
    db: Session = Depends(get_db),
    food_id: int,
) -> Any:
    """
    Récupérer un aliment par son ID.
    """
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Aliment non trouvé")
    return food

@router.put("/{food_id}", response_model=Food)
def update_food(
    *,
    db: Session = Depends(get_db),
    food_id: int,
    food_in: FoodCreate,
) -> Any:
    """
    Mettre à jour un aliment (ex: pour enrichir un brouillon).
    """
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Aliment non trouvé")
    
    update_data = food_in.model_dump(exclude_unset=True)
    # Si on met à jour, on considère généralement que ce n'est plus un brouillon
    if 'is_draft' not in update_data:
        update_data['is_draft'] = False
        
    for field, value in update_data.items():
        setattr(food, field, value)
        
    db.add(food)
    db.commit()
    db.refresh(food)
    return food
