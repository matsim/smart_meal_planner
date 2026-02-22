from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User as UserModel
from app.models.user import UserPreferences as PreferencesModel
from app.schemas.user import User, UserCreate, MetabolicProfile
from app.services.metabolic import calculate_metabolic_profile

router = APIRouter()

@router.post("/", response_model=User)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Créer un nouvel utilisateur avec ses préférences optionnelles.
    """
    # Vérifier l'email
    user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Un utilisateur avec cet email existe déjà.",
        )
        
    db_obj = UserModel(
        email=user_in.email,
        age=user_in.age,
        weight_kg=user_in.weight_kg,
        height_cm=user_in.height_cm,
        gender=user_in.gender,
        activity_level=user_in.activity_level,
        daily_meals_count=user_in.daily_meals_count,
        objective=user_in.objective
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    
    # Création des pref si elles sont fournies
    if user_in.preferences:
        pref_data = user_in.preferences.model_dump()
        db_pref = PreferencesModel(**pref_data, user_id=db_obj.id)
        db.add(db_pref)
        db.commit()
        db.refresh(db_obj)
        
    return db_obj


@router.get("/{user_id}", response_model=User)
def read_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
) -> Any:
    """
    Récupérer les informations d'un utilisateur par son ID.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
    return user


@router.get("/{user_id}/metabolisme", response_model=MetabolicProfile)
def read_metabolic_profile(
    *,
    db: Session = Depends(get_db),
    user_id: int,
) -> Any:
    """
    Retourne le calcul métabolique (BMR, TDEE, Macros cible) pour l'utilisateur.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    if not all([user.weight_kg, user.height_cm, user.age, user.gender]):
         raise HTTPException(
             status_code=400, 
             detail="Données physiologiques incomplètes pour le calcul (poids, taille, âge, sexe)."
         )
         
    return calculate_metabolic_profile(user)

from pydantic import BaseModel
class MetabolicUpdateFields(BaseModel):
    weight_kg: float = None
    height_cm: float = None
    age: int = None
    target_weekly_kcal: float = None

@router.put("/{user_id}/metabolisme", response_model=MetabolicProfile)
def update_metabolic_profile(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    data: MetabolicUpdateFields
) -> Any:
    """Met à jour les informations métaboliques (poids, taille, âge) et recalcule le profil."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    if data.weight_kg is not None:
        user.weight_kg = data.weight_kg
    if data.height_cm is not None:
        user.height_cm = data.height_cm
    if data.age is not None:
        user.age = data.age
    if data.target_weekly_kcal is not None:
        user.target_weekly_kcal = data.target_weekly_kcal
        
    db.commit()
    db.refresh(user)
    
    return calculate_metabolic_profile(user)

from app.models.user import DietaryConstraint as ConstraintModel
from app.schemas.user import DietaryConstraint, DietaryConstraintCreate

@router.get("/{user_id}/exclusions", response_model=List[DietaryConstraint])
def read_user_constraints(
    *,
    db: Session = Depends(get_db),
    user_id: int,
) -> Any:
    """Récupère les exclusions alimentaires (food_ids) de l'utilisateur."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
    return user.constraints

@router.post("/{user_id}/exclusions", response_model=DietaryConstraint)
def add_user_constraint(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    constraint_in: DietaryConstraintCreate
) -> Any:
    """Ajoute un aliment exclu aux contraintes de l'utilisateur."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    # Vérifier l'existence pour éviter les doublons
    existing = db.query(ConstraintModel).filter(
        ConstraintModel.user_id == user_id, 
        ConstraintModel.food_id == constraint_in.food_id
    ).first()
    
    if existing:
        return existing
        
    db_obj = ConstraintModel(user_id=user_id, food_id=constraint_in.food_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.delete("/{user_id}/exclusions/{food_id}")
def remove_user_constraint(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    food_id: int
) -> Any:
    """Supprime un aliment des exclusions de l'utilisateur."""
    constraint = db.query(ConstraintModel).filter(
        ConstraintModel.user_id == user_id,
        ConstraintModel.food_id == food_id
    ).first()
    
    if not constraint:
        raise HTTPException(status_code=404, detail="Contrainte non trouvée.")
        
    db.delete(constraint)
    db.commit()
    return {"success": True}
