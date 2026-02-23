from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.food import Food as FoodModel
from app.models.recipe import RecipeIngredient
from app.schemas.food import Food, FoodCreate, FoodMergeRequest

router = APIRouter()

@router.post("/", response_model=Food)
def create_food(
    *,
    db: Session = Depends(get_db),
    food_in: FoodCreate,
) -> Any:
    """
    Ajouter un nouvel aliment à la base (ex: depuis Ciqual).
    Intercepte les brouillons générés automatiquement pour chercher sur OpenFoodFacts.
    """
    food_data = food_in.model_dump()
    
    if food_data.get("is_draft", False):
        from app.services.openfoodfacts import search_food_off
        off_data = search_food_off(food_data["name"])
        if off_data:
            for field in ["energy_kcal", "proteins_g", "fat_g", "carbohydrates_g", "fiber_g"]:
                food_data[field] = off_data.get(field, 0.0)

    db_obj = FoodModel(**food_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[Food])
def list_foods(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    is_draft: bool = None,
    has_portions: bool = None
) -> Any:
    """
    Lister les aliments avec recherche optionnelle par nom.
    Retourne le header X-Total-Count pour la pagination.
    """
    from fastapi.responses import JSONResponse
    from typing import Optional
    query = db.query(FoodModel)
    if search:
        query = query.filter(FoodModel.name.ilike(f"%{search}%"))
    if is_draft is not None:
        query = query.filter(FoodModel.is_draft == is_draft)
    if has_portions is not None:
        from app.models.food_portion import FoodPortion
        from sqlalchemy import exists
        portion_exists = exists().where(FoodPortion.food_id == FoodModel.id)
        if has_portions:
            query = query.filter(portion_exists)
        else:
            query = query.filter(~portion_exists)
    total = query.count()
    items = query.order_by(FoodModel.name).offset(skip).limit(limit).all()
    
    from fastapi.encoders import jsonable_encoder
    return JSONResponse(
        content=jsonable_encoder(items),
        headers={"X-Total-Count": str(total), "Access-Control-Expose-Headers": "X-Total-Count"}
    )

@router.get("/search", response_model=List[Food])
def search_foods(
    q: str,
    db: Session = Depends(get_db),
    limit: int = 20
) -> Any:
    """
    Recherche rapide d'aliments par nom (ex: pour autocomplétion).
    Supporte la recherche multi-mots (ex: "huile tournesol" → "huile de tournesol").
    """
    from sqlalchemy import and_
    tokens = [t.strip() for t in q.split() if t.strip()]
    query = db.query(FoodModel)
    for token in tokens:
        query = query.filter(FoodModel.name.ilike(f"%{token}%"))
    # Trier par longueur de nom : les noms les plus courts sont généralement les plus génériques/pertinents
    query = query.order_by(FoodModel.name.asc())
    return query.limit(limit).all()

@router.get("/off/search")
def search_off_foods(
    q: str,
    limit: int = 5
) -> Any:
    """
    Recherche d'aliments sur OpenFoodFacts.
    """
    from app.services.openfoodfacts import search_many_food_off
    return search_many_food_off(q, limit=limit)

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

@router.delete("/{food_id}")
def delete_food(
    *,
    db: Session = Depends(get_db),
    food_id: int,
) -> Any:
    """
    Supprimer un aliment (ex: pour nettoyer les brouillons erronés).
    """
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Aliment non trouvé")
    
    db.delete(food)
    db.commit()
    return {"message": "Aliment supprimé avec succès"}

@router.post("/batch-delete")
def batch_delete_foods(
    *,
    db: Session = Depends(get_db),
    food_ids: List[int],
) -> Any:
    """
    Supprimer plusieurs aliments à la fois.
    """
    foods_to_delete = db.query(FoodModel).filter(FoodModel.id.in_(food_ids)).all()
    if not foods_to_delete:
        raise HTTPException(status_code=404, detail="Aucun aliment trouvé pour ces IDs")
    
    for food in foods_to_delete:
        db.delete(food)
    db.commit()
    return {"message": f"{len(foods_to_delete)} aliments supprimés avec succès"}

@router.post("/merge")
def merge_foods(
    *,
    db: Session = Depends(get_db),
    merge_req: FoodMergeRequest,
) -> Any:
    """
    Fusionner plusieurs aliments (sources) vers un seul (target).
    Met à jour toutes les recettes liées avant de supprimer les sources.
    """
    if len(merge_req.source_ids) < 1:
        raise HTTPException(status_code=400, detail="Il faut au moins un aliment source à fusionner")
        
    # Vérifier l'existence cible
    target_food = db.query(FoodModel).filter(FoodModel.id == merge_req.target_id).first()
    if not target_food:
        raise HTTPException(status_code=404, detail="Aliment cible non trouvé")
        
    # Récupérer les sources
    sources = db.query(FoodModel).filter(FoodModel.id.in_(merge_req.source_ids)).all()
    if not sources:
        raise HTTPException(status_code=404, detail="Aucun aliment source valide trouvé")
        
    # 1. Transférer les ingrédients de recettes
    source_ids_found = [s.id for s in sources]
    recipe_ingredients = db.query(RecipeIngredient).filter(RecipeIngredient.food_id.in_(source_ids_found)).all()
    
    for ri in recipe_ingredients:
        ri.food_id = target_food.id
        
    # 2. Supprimer les aliments sources
    for source in sources:
        db.delete(source)
        
    # 3. Commit de la transaction globale
    db.commit()
    
    return {"message": f"{len(sources)} aliments fusionnés avec succès"}
