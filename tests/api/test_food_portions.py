"""
Tests pour les endpoints /api/v1/foods/{food_id}/portions
Couvre : liste, création (is_default switching), mise à jour, suppression.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FOOD_PAYLOAD = {
    "name": "Farine de blé",
    "energy_kcal": 364.0,
    "proteins_g": 10.0,
    "fat_g": 1.0,
    "carbohydrates_g": 76.0,
    "fiber_g": 2.7,
    "water_g": 12.0,
}

PORTION_PAYLOAD = {
    "name": "1 tasse (125 ml)",
    "weight_g": 125.0,
    "is_default": False,
}


def _create_food(client):
    resp = client.post("/api/v1/foods/", json=FOOD_PAYLOAD)
    assert resp.status_code == 200
    return resp.json()


def _create_portion(client, food_id, overrides=None):
    data = {**PORTION_PAYLOAD, **(overrides or {})}
    resp = client.post(f"/api/v1/foods/{food_id}/portions", json=data)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Liste des portions
# ---------------------------------------------------------------------------

def test_list_portions_empty(client):
    """Un aliment sans portion retourne une liste vide."""
    food = _create_food(client)
    resp = client.get(f"/api/v1/foods/{food['id']}/portions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_portions_not_found(client):
    """GET portions pour un aliment inexistant → 404."""
    resp = client.get("/api/v1/foods/999999/portions")
    assert resp.status_code == 404


def test_list_portions_returns_all(client):
    """Les portions créées apparaissent dans la liste."""
    food = _create_food(client)
    _create_portion(client, food["id"], {"name": "1 cuillère à soupe", "weight_g": 12.0})
    _create_portion(client, food["id"], {"name": "1 tasse", "weight_g": 125.0})

    resp = client.get(f"/api/v1/foods/{food['id']}/portions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------

def test_create_portion(client):
    """POST crée une portion avec les bonnes données."""
    food = _create_food(client)
    resp = client.post(f"/api/v1/foods/{food['id']}/portions", json=PORTION_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == PORTION_PAYLOAD["name"]
    assert data["weight_g"] == PORTION_PAYLOAD["weight_g"]
    assert data["food_id"] == food["id"]


def test_create_portion_food_not_found(client):
    """POST sur aliment inexistant → 404."""
    resp = client.post("/api/v1/foods/999999/portions", json=PORTION_PAYLOAD)
    assert resp.status_code == 404


def test_create_default_portion_disables_previous_default(client):
    """Créer une portion is_default=True désactive l'ancienne portion par défaut."""
    food = _create_food(client)
    first = _create_portion(client, food["id"], {"name": "Portion A", "weight_g": 50.0, "is_default": True})
    assert first["is_default"] is True

    second = _create_portion(client, food["id"], {"name": "Portion B", "weight_g": 100.0, "is_default": True})
    assert second["is_default"] is True

    # L'ancienne portion par défaut doit avoir is_default=False
    portions = client.get(f"/api/v1/foods/{food['id']}/portions").json()
    defaults = [p for p in portions if p["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "Portion B"


def test_create_non_default_portion_does_not_affect_existing_default(client):
    """Créer une portion non-défaut ne modifie pas l'existante marquée défaut."""
    food = _create_food(client)
    _create_portion(client, food["id"], {"name": "Portion défaut", "weight_g": 50.0, "is_default": True})
    _create_portion(client, food["id"], {"name": "Autre portion", "weight_g": 200.0, "is_default": False})

    portions = client.get(f"/api/v1/foods/{food['id']}/portions").json()
    defaults = [p for p in portions if p["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "Portion défaut"


# ---------------------------------------------------------------------------
# Mise à jour
# ---------------------------------------------------------------------------

def test_update_portion(client):
    """PUT met à jour le nom et le poids d'une portion."""
    food = _create_food(client)
    portion = _create_portion(client, food["id"])
    portion_id = portion["id"]

    resp = client.put(
        f"/api/v1/foods/{food['id']}/portions/{portion_id}",
        json={"name": "Mis à jour", "weight_g": 75.0, "is_default": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Mis à jour"
    assert data["weight_g"] == 75.0


def test_update_portion_not_found(client):
    """PUT sur une portion inexistante → 404."""
    food = _create_food(client)
    resp = client.put(
        f"/api/v1/foods/{food['id']}/portions/999999",
        json={"name": "X", "weight_g": 50.0, "is_default": False},
    )
    assert resp.status_code == 404


def test_update_portion_default_switching(client):
    """PUT avec is_default=True désactive la précédente portion par défaut."""
    food = _create_food(client)
    p1 = _create_portion(client, food["id"], {"name": "Ancienne défaut", "weight_g": 50.0, "is_default": True})
    p2 = _create_portion(client, food["id"], {"name": "Nouvelle défaut", "weight_g": 100.0, "is_default": False})

    # Mettre p2 comme défaut
    resp = client.put(
        f"/api/v1/foods/{food['id']}/portions/{p2['id']}",
        json={"name": "Nouvelle défaut", "weight_g": 100.0, "is_default": True},
    )
    assert resp.status_code == 200

    portions = client.get(f"/api/v1/foods/{food['id']}/portions").json()
    defaults = [p for p in portions if p["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == p2["id"]


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

def test_delete_portion(client):
    """DELETE supprime la portion."""
    food = _create_food(client)
    portion = _create_portion(client, food["id"])
    portion_id = portion["id"]

    resp = client.delete(f"/api/v1/foods/{food['id']}/portions/{portion_id}")
    assert resp.status_code == 204

    # La portion ne doit plus apparaître dans la liste
    portions = client.get(f"/api/v1/foods/{food['id']}/portions").json()
    assert all(p["id"] != portion_id for p in portions)


def test_delete_portion_not_found(client):
    """DELETE sur une portion inexistante → 404."""
    food = _create_food(client)
    resp = client.delete(f"/api/v1/foods/{food['id']}/portions/999999")
    assert resp.status_code == 404


def test_delete_portion_wrong_food(client):
    """DELETE avec food_id ne correspondant pas à la portion → 404."""
    food1 = _create_food(client)
    food2 = client.post("/api/v1/foods/", json={**FOOD_PAYLOAD, "name": "Autre aliment"}).json()
    portion = _create_portion(client, food1["id"])

    # Essayer de supprimer avec food2 → portion n'appartient pas à food2
    resp = client.delete(f"/api/v1/foods/{food2['id']}/portions/{portion['id']}")
    assert resp.status_code == 404
