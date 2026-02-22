# Smart Meal Planner

Une application "API-First" de planification alimentaire intelligente et d'aide à la conception de repas (Batch Cooking).

## Architecture API-First

Le projet adopte une séparation stricte des responsabilités métier :

- **Backend / API (Dossier `app/`)** : Construit avec **FastAPI** et **Python**. L'API modulaire gère de manière autonome la base de données (PostgreSQL/SQLite via SQLAlchemy), les calculs métaboliques, le solveur algorithmique de menus (via PuLP) et le scraping intelligent de recettes. Toute la logique métier et la sécurité y résident.
- **Frontend / Interface Client (Dossier `frontend/`)** : Développé en **React**, **TypeScript** et animé par **Vite**. L'interface (en mode Glassmorphism) ne fait que consommer les endpoints REST de l'API FastAPI et se met à jour en temps réel.

## Découpage des dépendances

Afin de préserver cette encapsulation, les exigences logicielles sont réparties :
- Frontend : `frontend/package.json`
- Backend : `app/requirements.txt` (et dérivés : `requirements-scraper.txt`, etc.).

## Démarrage rapide

### 1. Démarrer le Serveur Backend (FastAPI)
Ouvrez un terminal à la racine du projet :
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r app/requirements.txt
uvicorn app.main:app --reload
```
> L'API REST est maintenant disponible sur `http://localhost:8000`. Les spécifications interactives Swagger sont consultables sur `http://localhost:8000/docs`.

### 2. Démarrer le Serveur Frontend (React)
Ouvrez un second terminal, placez-vous dans le dossier web :
```bash
cd frontend
npm install
npm run dev
```
> L'application client est maintenant accessible via votre navigateur sur `http://localhost:5173`.
