.PHONY: dev test test-cov reset-db reset-db-force seed migrate help

# ─────────────────────────────────────────────
#  Développement
# ─────────────────────────────────────────────

dev:                         ## Lance le serveur FastAPI en mode rechargement automatique
	uvicorn app.main:app --reload

# ─────────────────────────────────────────────
#  Tests
# ─────────────────────────────────────────────

test:                        ## Lance la suite de tests (base en mémoire, isolée par test)
	python -m pytest tests/ -q

test-cov:                    ## Lance les tests avec rapport de couverture HTML
	python -m pytest tests/ -q --cov=app --cov-report=html --cov-report=term-missing
	@echo "Rapport : htmlcov/index.html"

test-v:                      ## Lance les tests en mode verbeux
	python -m pytest tests/ -v

# ─────────────────────────────────────────────
#  Base de données
# ─────────────────────────────────────────────

migrate:                     ## Applique les migrations Alembic (alembic upgrade head)
	alembic upgrade head

seed:                        ## Charge les données initiales (aliments + recettes stub)
	python seed.py

reset-db:                    ## Réinitialise la BDD avec confirmation interactive, puis reseed
	python scripts/reset_db.py

reset-db-force:              ## Réinitialise la BDD SANS confirmation (CI / scripts)
	python scripts/reset_db.py --force

# ─────────────────────────────────────────────
#  Aide
# ─────────────────────────────────────────────

help:                        ## Affiche ce message d'aide
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
