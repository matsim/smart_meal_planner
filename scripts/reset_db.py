#!/usr/bin/env python3
"""
Réinitialise la base de données Smart Meal Planner.

Usage :
  python scripts/reset_db.py              # Confirmation interactive
  python scripts/reset_db.py --force      # Sans confirmation
  python scripts/reset_db.py --no-seed    # Reset sans données initiales
  python scripts/reset_db.py --no-migrate # Reset sans appliquer les migrations
"""
import sys
import os
import json
import argparse
import subprocess

# Ajouter la racine du projet au path Python
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

def _confirm(message: str) -> bool:
    try:
        rep = input(f"{message} [oui/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAnnulé.")
        return False
    return rep in ("oui", "o", "yes", "y")


# ---------------------------------------------------------------------------
# Étape 1 : Supprimer / vider la base
# ---------------------------------------------------------------------------

def _reset_sqlite(db_path: str) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"  ✓ Fichier supprimé : {db_path}")
    else:
        print(f"  ✓ Aucun fichier existant ({db_path})")


def _reset_postgresql(db_url: str) -> None:
    from sqlalchemy import create_engine
    from app.models.base import Base
    import app.models  # noqa : charge tous les modèles pour que Base.metadata soit complet

    engine = create_engine(db_url)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    print("  ✓ Toutes les tables supprimées (PostgreSQL)")


def reset_database(db_url: str) -> None:
    print("\n[1/3] Suppression de la base de données...")
    if db_url.startswith("sqlite:///"):
        raw_path = db_url[len("sqlite:///"):]
        db_path = raw_path if os.path.isabs(raw_path) else os.path.join(os.getcwd(), raw_path)
        _reset_sqlite(db_path)
    elif db_url.startswith("postgresql"):
        _reset_postgresql(db_url)
    else:
        print(f"  ✗ Type de base non supporté : {db_url}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Étape 2 : Migrations Alembic
# ---------------------------------------------------------------------------

def run_migrations() -> None:
    print("\n[2/3] Application des migrations Alembic...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ✗ Erreur Alembic :\n{result.stderr}")
        sys.exit(1)
    print("  ✓ Schéma à jour (alembic upgrade head)")


# ---------------------------------------------------------------------------
# Étape 3 : Données initiales (seed)
# ---------------------------------------------------------------------------

def seed_foods(db_url: str) -> None:
    print("\n[3/3] Chargement des données initiales...")

    seed_file = os.path.join(PROJECT_ROOT, "app", "db", "seed_foods.json")
    if not os.path.exists(seed_file):
        print(f"  ⚠  Fichier introuvable : {seed_file} — seed ignoré")
        return

    with open(seed_file, "r", encoding="utf-8") as fh:
        foods_data = json.load(fh)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.food import Food

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inserted = 0
        for fd in foods_data:
            if not db.query(Food).filter(Food.name == fd["name"]).first():
                db.add(Food(**fd))
                inserted += 1
        db.commit()
        skipped = len(foods_data) - inserted
        print(f"  ✓ {inserted} aliment(s) insérés, {skipped} déjà présent(s)")
    except Exception as exc:
        db.rollback()
        print(f"  ✗ Erreur lors du seed : {exc}")
        sys.exit(1)
    finally:
        db.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Réinitialise la base de données Smart Meal Planner"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Pas de confirmation interactive",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Ne pas charger les données initiales après le reset",
    )
    parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="Ne pas appliquer les migrations Alembic",
    )
    args = parser.parse_args()

    from app.core.config import settings
    db_url: str = settings.SQLALCHEMY_DATABASE_URI or "sqlite:///./sql_app.db"

    print(f"Base de données cible : {db_url}")
    print("ATTENTION : toutes les données existantes seront perdues.")

    if not args.force and not _confirm("Confirmer la réinitialisation ?"):
        print("Annulé.")
        sys.exit(0)

    reset_database(db_url)

    if not args.no_migrate:
        run_migrations()

    if not args.no_seed:
        seed_foods(db_url)

    print("\n✓ Base de données réinitialisée avec succès.\n")


if __name__ == "__main__":
    main()
