"""
Script de seed des portions nommées (FoodPortion) pour les aliments CIQUAL.
Source des poids : USDA FoodData Central + Manuel de conversion ANSES.
Utilisation : python scripts/seed_portions.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.food import Food as FoodModel
from app.models.food_portion import FoodPortion as FoodPortionModel
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Données de portions : {nom_fragment: [(label_portion, poids_g, is_default), ...]}
# nom_fragment est comparé en ILIKE %fragment% au nom de l'aliment CIQUAL
# ---------------------------------------------------------------------------
PORTIONS_DATA: list[tuple[list[str], list[tuple[str, float, bool]]]] = [

    # ── Agrumes ──────────────────────────────────────────────────────────────
    (["citron vert", "lime"], [
        ("1 petit",  44.0, False),
        ("1 moyen",  67.0, True),
        ("1 grand",  90.0, False),
        ("1 c.à.s de jus", 15.0, False),
    ]),
    (["citron jaune", "citron, cru"], [
        ("1 petit",  58.0, False),
        ("1 moyen",  84.0, True),
        ("1 grand", 108.0, False),
        ("1 c.à.s de jus", 15.0, False),
    ]),
    (["orange, crue", "orange entière"], [
        ("1 petite", 96.0, False),
        ("1 moyenne", 131.0, True),
        ("1 grande",  184.0, False),
    ]),
    (["pamplemousse"], [
        ("1 moyen", 246.0, True),
        ("1 demi", 123.0, False),
    ]),
    (["mandarine", "clémentine"], [
        ("1 petite",  47.0, False),
        ("1 moyenne", 74.0, True),
        ("1 grande",  95.0, False),
    ]),

    # ── Fruits frais ─────────────────────────────────────────────────────────
    (["pomme, crue", "pomme entière"], [
        ("1 petite",  100.0, False),
        ("1 moyenne", 138.0, True),
        ("1 grande",  212.0, False),
    ]),
    (["poire, crue"], [
        ("1 petite",  100.0, False),
        ("1 moyenne", 166.0, True),
        ("1 grande",  209.0, False),
    ]),
    (["banane, crue"], [
        ("1 petite",  81.0, False),
        ("1 moyenne", 118.0, True),
        ("1 grande",  136.0, False),
    ]),
    (["fraise, crue"], [
        ("1 fraise moyenne", 12.0, True),
        ("1 tasse (entières)", 149.0, False),
    ]),
    (["framboise"], [
        ("1 framboise", 2.5, True),
        ("1 tasse", 123.0, False),
    ]),
    (["myrtille", "bleuet"], [
        ("1 myrtille", 1.5, False),
        ("1 tasse", 148.0, True),
    ]),
    (["raisin, cru"], [
        ("1 grain",  3.0, False),
        ("10 grains", 30.0, False),
        ("1 grappe (petite)", 80.0, True),
    ]),
    (["avocat, cru"], [
        ("1 demi",  100.0, False),
        ("1 entier", 201.0, True),
        ("1 tranche", 28.0, False),
    ]),
    (["mangue, crue"], [
        ("1 tranche épaisse", 60.0, True),
        ("1 mangue entière", 336.0, False),
        ("1 tasse, coupée", 165.0, False),
    ]),
    (["kiwi, cru"], [
        ("1 petit",  50.0, False),
        ("1 moyen",  69.0, True),
        ("1 grand",  91.0, False),
    ]),
    (["ananas, cru"], [
        ("1 tranche",  82.0, True),
        ("1 tasse, coupé", 165.0, False),
    ]),
    (["pêche, crue"], [
        ("1 petite",  98.0, False),
        ("1 moyenne", 147.0, True),
    ]),
    (["prune, crue"], [
        ("1 prune",  66.0, True),
        ("4 prunes", 264.0, False),
    ]),
    (["abricot, cru"], [
        ("1 abricot", 35.0, True),
        ("3 abricots", 105.0, False),
    ]),
    (["pastèque, crue"], [
        ("1 tranche",  280.0, True),
        ("1 tasse, cubes", 152.0, False),
    ]),
    (["melon, cru"], [
        ("1 tranche",  170.0, True),
        ("1 tasse, cubes", 177.0, False),
    ]),

    # ── Légumes ──────────────────────────────────────────────────────────────
    (["tomate, crue", "tomate entière"], [
        ("1 petite",  91.0, False),
        ("1 moyenne", 123.0, True),
        ("1 grande",  182.0, False),
        ("1 tomate cerise", 17.0, False),
    ]),
    (["oignon, cru"], [
        ("1 petit",  70.0, False),
        ("1 moyen", 110.0, True),
        ("1 grand",  150.0, False),
    ]),
    (["ail, cru"], [
        ("1 gousse",   5.0, True),
        ("1 tête (entière)", 40.0, False),
    ]),
    (["échalote", "shallot"], [
        ("1 échalote", 30.0, True),
    ]),
    (["poivron, cru"], [
        ("1 petit",  74.0, False),
        ("1 moyen", 119.0, True),
        ("1 grand",  164.0, False),
    ]),
    (["concombre, cru"], [
        ("1 tranches",  19.0, False),
        ("1 moyen (entier)", 301.0, True),
        ("1 demi",  150.0, False),
    ]),
    (["courgette, crue"], [
        ("1 petite", 118.0, False),
        ("1 moyenne", 196.0, True),
        ("1 grande",  261.0, False),
    ]),
    (["carotte, crue"], [
        ("1 petite", 50.0, False),
        ("1 moyenne", 61.0, True),
        ("1 grande",  72.0, False),
    ]),
    (["pomme de terre, crue"], [
        ("1 petite",  85.0, False),
        ("1 moyenne", 148.0, True),
        ("1 grande",  213.0, False),
    ]),
    (["aubergine, crue"], [
        ("1 petite",  160.0, False),
        ("1 moyenne", 458.0, True),
    ]),
    (["champignon, cru", "champignon de paris"], [
        ("1 champignon moyen", 18.0, True),
        ("1 tasse, tranchés", 70.0, False),
    ]),
    (["brocoli, cru"], [
        ("1 fleurette", 11.0, True),
        ("1 tasse", 91.0, False),
    ]),
    (["chou-fleur, cru"], [
        ("1 fleurette", 13.0, True),
        ("1 tasse", 107.0, False),
    ]),
    (["épinard, cru"], [
        ("1 feuille", 10.0, True),
        ("1 tasse, cru", 30.0, False),
    ]),
    (["radis, cru"], [
        ("1 radis", 4.5, True),
        ("10 radis", 45.0, False),
    ]),

    # ── Herbes fraîches ──────────────────────────────────────────────────────
    (["coriandre, fraîche", "coriandre fraîche"], [
        ("1 brin",    2.0, False),
        ("1 bouquet", 25.0, True),
        ("1 c.à.s ciselée", 5.0, False),
    ]),
    (["persil, frais", "persil frais"], [
        ("1 brin",    5.0, False),
        ("1 bouquet", 40.0, True),
        ("1 c.à.s ciselé", 4.0, False),
    ]),
    (["basilic, frais"], [
        ("1 feuille",   1.0, False),
        ("1 bouquet",  20.0, True),
        ("1 c.à.s ciselé", 3.0, False),
    ]),
    (["menthe, fraîche"], [
        ("1 feuille",  0.5, False),
        ("1 bouquet", 20.0, True),
        ("1 c.à.s ciselée", 5.0, False),
    ]),
    (["thym, frais"], [
        ("1 brin",    1.5, True),
        ("1 c.à.c séchée", 2.0, False),
    ]),
    (["romarin, frais"], [
        ("1 brin",    2.5, True),
        ("1 c.à.c séchée", 2.0, False),
    ]),
    (["ciboulette, fraîche"], [
        ("1 brin",    0.3, False),
        ("1 c.à.s ciselée", 3.0, True),
    ]),
    (["estragon, frais"], [
        ("1 brin",   1.0, True),
        ("1 c.à.s", 4.0, False),
    ]),

    # ── Produits laitiers ────────────────────────────────────────────────────
    (["oeuf, entier, cru", "oeuf de poule"], [
        ("1 petit",   38.0, False),
        ("1 moyen",   50.0, False),
        ("1 grand",   60.0, True),
        ("1 très grand", 70.0, False),
    ]),
    (["beurre, "], [
        ("1 noix (env. 5g)", 5.0, False),
        ("1 c.à.c",  5.0, False),
        ("1 c.à.s",  14.0, True),
    ]),

    # ── Légumineuses (cuites) ────────────────────────────────────────────────
    (["lentille, cuite"], [
        ("1 tasse", 198.0, True),
        ("1 c.à.s", 12.0, False),
    ]),
    (["pois chiche, cuit"], [
        ("1 tasse", 240.0, True),
        ("1 c.à.s", 15.0, False),
    ]),
    (["haricot rouge, cuit"], [
        ("1 tasse", 256.0, True),
        ("1 c.à.s", 16.0, False),
    ]),

    # ── Viandes ──────────────────────────────────────────────────────────────
    (["poulet, blanc, cru"], [
        ("1 escalope", 120.0, True),
        ("1 portion (100g)", 100.0, False),
    ]),
    (["boeuf, haché"], [
        ("1 steak haché", 100.0, True),
        ("1 boulette", 30.0, False),
    ]),

    # ── Épices & condiments ──────────────────────────────────────────────────
    (["gingembre, cru"], [
        ("1 tranche mince",  5.0, True),
        ("1 c.à.c râpé",     2.0, False),
        ("1 c.à.s râpé",     6.0, False),
    ]),
    (["piment, rouge, cru"], [
        ("1 petit piment",  10.0, True),
        ("1 moyen",   20.0, False),
    ]),
]

# ---------------------------------------------------------------------------

def seed_portions(db: Session):
    total_created = 0
    total_skipped = 0

    for fragments, portions in PORTIONS_DATA:
        # Chercher les aliments dont le nom contient l'un des fragments
        query = db.query(FoodModel)
        from sqlalchemy import or_
        conditions = [FoodModel.name.ilike(f"%{frag}%") for frag in fragments]
        matching_foods = query.filter(or_(*conditions)).all()

        if not matching_foods:
            print(f"  [SKIP] Aucun aliment trouvé pour : {fragments}")
            continue

        for food in matching_foods:
            # Vérifier si des portions existent déjà (éviter doublons)
            existing = db.query(FoodPortionModel).filter(FoodPortionModel.food_id == food.id).count()
            if existing > 0:
                total_skipped += 1
                continue

            for (name, weight_g, is_default) in portions:
                db.add(FoodPortionModel(
                    food_id=food.id,
                    name=name,
                    weight_g=weight_g,
                    is_default=is_default
                ))
            total_created += 1
            print(f"  [OK] {food.name} → {len(portions)} portions")

    db.commit()
    print(f"\n✅ Seed terminé : {total_created} aliments enrichis, {total_skipped} ignorés (déjà renseignés)")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_portions(db)
    finally:
        db.close()
