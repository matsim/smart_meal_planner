from typing import Dict, Any, Optional

# Un système de stockage temporaire en mémoire pour le suivi des tâches (TDD phase)
tasks_store: Dict[str, dict] = {}

def create_task(task_id: str) -> None:
    """Initialise une nouvelle tâche avec le statut pending."""
    tasks_store[task_id] = {"status": "pending", "data": None, "error": None}

def update_task_status(task_id: str, status: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
    """Met à jour le statut, et éventuellement les données ou l'erreur associée."""
    if task_id in tasks_store:
        tasks_store[task_id]["status"] = status
        if data is not None:
            tasks_store[task_id]["data"] = data
        if error is not None:
            tasks_store[task_id]["error"] = error

def get_task_status(task_id: str) -> Optional[dict]:
    """Récupère l'état actuel d'une tâche."""
    return tasks_store.get(task_id)
