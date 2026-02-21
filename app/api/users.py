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


@router.get("/{user_id}/metabolic-profile", response_model=MetabolicProfile)
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
