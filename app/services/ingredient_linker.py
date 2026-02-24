"""
Liaison automatique ingrédients scrappés → aliments DB.

Algorithme multi-niveaux (score ∈ [0.0, 1.0]) :
  1. Exact match        – ilike(product_name), score 1.0
  2. Token AND          – tous les tokens normalisés du produit présents dans food.name
  3. Token OR           – au moins un token significatif présent (fallback)

Le score composite combine :
  - recouvrement de tokens (proportion des mots du produit retrouvés dans food.name)
  - similarité séquentielle (difflib SequenceMatcher sur les chaînes normalisées)

Résultats triés par score décroissant, dédoublonnés par food_id.

Conversion d'unité (raw_quantity + raw_unit → grammes) :
  - Unités masse directes (g, kg)      → conversion exacte
  - Volumes (ml, cl, l)                → via densité de l'aliment (défaut 1 g/ml)
  - Mesures culinaires (c.à.s, c.à.c) → valeurs approchées standard
  - Comptage sans unité connue         → portion_weight_g de l'aliment
  - Inconvertible                      → None (l'appelant fournit le fallback)
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.food import Food

# ---------------------------------------------------------------------------
# Mots vides ignorés lors de la comparaison des noms
# ---------------------------------------------------------------------------

# On ne conserve que les mots grammaticaux neutres.
# Les modificateurs culinaires (haché, rôti, cru…) sont intentionnellement
# conservés : ils participent à la sémantique et améliorent la précision du score.
_STOP_WORDS = {
    "de", "du", "des", "d", "la", "le", "les", "l",
    "un", "une", "et", "ou",
    "a", "au", "aux", "en", "avec", "sans", "sur", "par", "pour", "dans",
}

# Ligatures françaises : NFD ne les décompose pas, remplacement explicite requis
_LIGATURES: Dict[str, str] = {
    "œ": "oe", "Œ": "oe",
    "æ": "ae", "Æ": "ae",
}

# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Minuscule, ligatures, suppression des accents et des mots vides."""
    # Remplacement explicite des ligatures (non décomposables par NFD)
    for lig, repl in _LIGATURES.items():
        text = text.replace(lig, repl)
    text = text.lower().strip()
    # Décomposition NFD → suppression des marques combinantes (accents)
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Conserver uniquement lettres, chiffres, espaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in _STOP_WORDS]
    return " ".join(tokens)

# ---------------------------------------------------------------------------
# Score composite
# ---------------------------------------------------------------------------

def _composite_score(product_norm: str, food_name: str) -> float:
    """Score composite [0.0, 1.0] entre un nom de produit normalisé et food.name."""
    food_norm = _normalize(food_name)
    if not product_norm or not food_norm:
        return 0.0
    if product_norm == food_norm:
        return 1.0

    product_tokens = set(product_norm.split())
    food_tokens = set(food_norm.split())

    # Recouvrement : proportion des tokens du produit présents dans food
    if product_tokens:
        overlap = len(product_tokens & food_tokens) / len(product_tokens)
        # Bonus de précision : food.name d'autant plus court que le produit
        specificity = 1.0 / (1.0 + max(0, len(food_tokens) - len(product_tokens)))
        token_score = overlap * (0.7 + 0.3 * specificity)
    else:
        token_score = 0.0

    # Similarité séquentielle sur les chaînes normalisées
    seq_score = SequenceMatcher(None, product_norm, food_norm).ratio()

    return round(0.6 * token_score + 0.4 * seq_score, 3)

# ---------------------------------------------------------------------------
# Recherche principale
# ---------------------------------------------------------------------------

def find_food_matches(
    product_name: str,
    db: Session,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Trouve les meilleurs aliments DB correspondant à un nom d'ingrédient scrappé.

    Retourne une liste triée par score décroissant :
      [{"food_id": int, "food_name": str, "score": float, "match_type": str}]
    """
    if not product_name or not product_name.strip():
        return []

    product_name = product_name.strip()
    product_norm = _normalize(product_name)
    product_tokens = [t for t in product_norm.split() if len(t) >= 2]

    results: Dict[int, Dict[str, Any]] = {}

    # ── Étape 1 : Exact match (insensible à la casse)
    exact = db.query(Food).filter(Food.name.ilike(product_name)).first()
    if exact:
        results[exact.id] = {
            "food_id": exact.id,
            "food_name": exact.name,
            "score": 1.0,
            "match_type": "exact",
        }

    # ── Étape 2 : Tous les tokens normalisés présents dans food.name (AND)
    if product_tokens:
        q = db.query(Food)
        for token in product_tokens:
            q = q.filter(Food.name.ilike(f"%{token}%"))
        for food in q.limit(30).all():
            if food.id not in results:
                score = _composite_score(product_norm, food.name)
                results[food.id] = {
                    "food_id": food.id,
                    "food_name": food.name,
                    "score": score,
                    "match_type": "token",
                }

    # ── Étape 3 : Fallback token par token (OR) sur les termes les plus courts
    #    Couvre les cas où un seul mot-clé suffit à identifier l'aliment
    if len(results) < limit and product_tokens:
        # Trier par longueur croissante : les tokens courts sont plus discriminants
        key_tokens = sorted(product_tokens, key=len)[:2]
        for token in key_tokens:
            for food in db.query(Food).filter(Food.name.ilike(f"%{token}%")).limit(20).all():
                if food.id not in results:
                    score = _composite_score(product_norm, food.name)
                    if score >= 0.25:  # Seuil minimal pour filtrer le bruit
                        results[food.id] = {
                            "food_id": food.id,
                            "food_name": food.name,
                            "score": score,
                            "match_type": "fuzzy",
                        }

    sorted_results = sorted(results.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:limit]

# ---------------------------------------------------------------------------
# Conversion d'unité → grammes
# ---------------------------------------------------------------------------

# Facteurs de conversion directs (vers grammes ou millilitres ≈ grammes)
_UNIT_TO_G: Dict[str, float] = {
    "g":      1.0,
    "kg":     1000.0,
    "mg":     0.001,
    "c.a.s":  15.0,   # cuillère à soupe ≈ 15 ml/g
    "c.a.c":  5.0,    # cuillère à café  ≈ 5 ml/g
    "tasse":  240.0,  # tasse standard (240 ml)
    "verre":  200.0,
    "bol":    350.0,
    "pincee": 0.5,
    "filet":  5.0,
    "noix":   10.0,
    "zeste":  3.0,
    "ml":     1.0,
    "cl":     10.0,
    "l":      1000.0,
}

# Alias → clé canonique dans _UNIT_TO_G
_UNIT_ALIASES: Dict[str, str] = {
    # Masse
    "gramme": "g", "grammes": "g",
    "kilogramme": "kg", "kilogrammes": "kg",
    # Volume
    "litre": "l", "litres": "l",
    "millilitre": "ml", "millilitres": "ml",
    "centilitre": "cl", "centilitres": "cl",
    # Culinaire — variantes normalisées (accents retirés)
    "c.a.s": "c.a.s", "cas": "c.a.s", "cas": "c.a.s",
    "cs": "c.a.s", "c.a.c": "c.a.c", "cac": "c.a.c", "cc": "c.a.c",
    "cuillere a soupe": "c.a.s",
    "cuilleres a soupe": "c.a.s",
    "cuillere a cafe": "c.a.c",
    "cuilleres a cafe": "c.a.c",
    # Avec accents (tels que retournés par ingredient_parser)
    "c.à.s": "c.a.s",
    "c.à.c": "c.a.c",
    "pincée": "pincee", "pincees": "pincee",
}

# Volumes (nécessitent la densité de l'aliment pour une conversion précise)
_VOLUME_UNITS = {"ml", "cl", "l"}


def convert_to_grams(
    raw_quantity: Optional[float],
    raw_unit: Optional[str],
    food: Optional[Any] = None,  # Food ORM object ou duck-type compatible
) -> Optional[float]:
    """
    Convertit (quantité brute, unité) en grammes.

    Retourne None si la conversion est impossible.
    L'appelant est responsable de fournir une valeur de secours.
    """
    if not raw_quantity or raw_quantity <= 0:
        return None

    # Normalisation de l'unité
    unit_raw = (raw_unit or "").strip().lower()
    # Supprimer les accents pour unifier c.à.s / c.a.s etc.
    unit_norm = "".join(
        c for c in unicodedata.normalize("NFD", unit_raw)
        if unicodedata.category(c) != "Mn"
    )
    unit_key = _UNIT_ALIASES.get(unit_norm, _UNIT_ALIASES.get(unit_raw, unit_norm))

    if unit_key in _UNIT_TO_G:
        base_g = _UNIT_TO_G[unit_key] * raw_quantity
        # Pour les volumes, appliquer la densité de l'aliment si disponible
        if unit_key in _VOLUME_UNITS and food is not None:
            density = getattr(food, "density", None)
            if density:
                base_g *= density
        return round(base_g, 2)

    # Unité de comptage ou inconnue → utiliser la portion standard de l'aliment
    if food is not None:
        portion_weight = getattr(food, "portion_weight_g", None)
        if portion_weight and portion_weight > 0:
            return round(raw_quantity * portion_weight, 2)

    return None
