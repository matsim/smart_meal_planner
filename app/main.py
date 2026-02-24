import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import api_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Gestionnaires d'erreurs — messages lisibles pour l'utilisateur
# ---------------------------------------------------------------------------

def _field_path(loc: tuple) -> str:
    """Construit un chemin lisible depuis la liste de localisations Pydantic."""
    parts = [str(l) for l in loc if l != "body"]
    return " → ".join(parts) if parts else "champ inconnu"


_PYDANTIC_MSG_FR = {
    "field required":                   "Ce champ est obligatoire",
    "value is not a valid integer":      "Doit être un nombre entier",
    "value is not a valid float":        "Doit être un nombre décimal",
    "value is not a valid enum member":  "Valeur non reconnue pour ce champ",
    "none is not an allowed value":      "Ce champ ne peut pas être vide",
    "value error":                       "Valeur invalide",
    "string too short":                  "Texte trop court",
    "string too long":                   "Texte trop long",
    "ensure this value is greater than 0": "La valeur doit être supérieure à 0",
}


def _translate(msg: str) -> str:
    msg_low = msg.lower()
    for key, fr in _PYDANTIC_MSG_FR.items():
        if key in msg_low:
            return fr
    return msg  # fallback : message original (anglais)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Transforme les erreurs de validation Pydantic en réponse lisible par l'utilisateur."""
    errors = [
        {"champ": _field_path(e["loc"]), "message": _translate(e["msg"])}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Données invalides. Corrigez les champs indiqués et réessayez.",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Capture toute exception non traitée : retourne un message structuré, jamais un 500 vide."""
    logger.error(
        "Exception non gérée sur %s %s : %s",
        request.method, request.url, exc, exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Une erreur inattendue s'est produite. "
                "Vérifiez les données saisies et réessayez. "
                "Si le problème persiste, consultez les logs du serveur."
            ),
            "error_type": type(exc).__name__,
        },
    )


@app.get("/")
def root():
    return {"message": "Welcome to Smart Meal Planner API"}
