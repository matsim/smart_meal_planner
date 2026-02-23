import re
from typing import Dict, Any, Optional

# Unités courantes en cuisine française tolérant les typos (cuilere, cuillere, etc.)
UNITS = [
    r"cui[l]+[èe]re(?:s)?\s+à\s+soupe", r"c\.à\.s", r"c\.a\.s", r"càs", r"cas", r"cs",
    r"cui[l]+[èe]re(?:s)?\s+à\s+café", r"c\.à\.c", r"c\.a\.c", r"càc", r"cac", r"cc",
    r"gramme(?:s)?", r"\bg\b", r"\bkg\b", r"kilogramme(?:s)?",
    r"litre(?:s)?", r"\bl\b", r"\bml\b", r"millilitre(?:s)?", r"\bcl\b", r"centilitre(?:s)?",
    r"tasse(?:s)?", r"verre(?:s)?", r"bol(?:s)?", r"pincée(?:s)?",
    r"gousse(?:s)?", r"tranche(?:s)?", r"filet(?:s)?", r"feuille(?:s)?",
    r"brin(?:s)?", r"poignée(?:s)?", r"noix", r"zeste(?:s)?", r"boîte(?:s)?"
]

# Assemblage de l'expression régulière pour l'unité
UNITS_REGEX = r"(?P<unit>" + r"|".join(UNITS) + r")"
# Gère les fractions (ex: 1/2), les décimaux (1.5 ou 1,5), etc. 
QTY_REGEX = r"(?P<qty>\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)"
# Séparateur optionnel ("de", "d'")
SEP_REGEX = r"(?:\s+(?:de|d')\s*|\s+)"

# Pattern complet
# Ex: "1.5 kg de pommes" -> qty=1.5, unit=kg, product=pommes
# Ex: "4 cas sauce soja" -> qty=4, unit=cas, product=sauce soja
# Ex: "3 pommes" -> qty=3, unit=None, product=pommes
PATTERN_QTY_UNIT = re.compile(rf"^\s*{QTY_REGEX}\s*{UNITS_REGEX}{SEP_REGEX}(?P<product>.*)$", re.IGNORECASE)
PATTERN_QTY_ONLY = re.compile(rf"^\s*{QTY_REGEX}\s+(?P<product>.*)$", re.IGNORECASE)

def parse_fraction(val_str: str) -> float:
    """Convertit '1/2' ou '1,5' en float."""
    val_str = val_str.replace(",", ".").replace(" ", "")
    if "/" in val_str:
        num, den = val_str.split("/")
        return float(num) / float(den)
    return float(val_str)

def normalize_unit(unit: str) -> str:
    """Normalise une chaîne d'unité pour avoir un format constant (ex: 'cas' -> 'c.à.s')."""
    if not unit:
        return unit
    u = unit.lower().strip()
    if re.search(r"cui[l]+[èe]re(?:s)?\s+à\s+soupe|c\.?à\.?s\.?|c\.?a\.?s\.?|cs", u):
        return "c.à.s"
    if re.search(r"cui[l]+[èe]re(?:s)?\s+à\s+café|c\.?à\.?c\.?|c\.?a\.?c\.?|cc", u):
        return "c.à.c"
    if re.search(r"^g$|^gramme(?:s)?$", u):
        return "g"
    if re.search(r"^kg$|^kilogramme(?:s)?$", u):
        return "kg"
    if re.search(r"^ml$|^millilitre(?:s)?$", u):
        return "ml"
    if re.search(r"^cl$|^centilitre(?:s)?$", u):
        return "cl"
    if re.search(r"^l$|^litre(?:s)?$", u):
        return "L"
    if re.search(r"^pincée(?:s)?$", u):
        return "pincée"
    
    # Par défaut, retourner le mot en minuscule avec la première lettre majuscule s'il est long
    return u.capitalize() if len(u) > 2 else u

def parse_ingredient(raw_string: str) -> Dict[str, Any]:
    """
    Parse une chaîne brute d'ingrédient et extrait quantité, unité et nom du produit.
    """
    raw_string = raw_string.strip()
    
    # 1. Test Pattern (Quantité + Unité + Produit)
    match = PATTERN_QTY_UNIT.search(raw_string)
    if match:
        qty_str = match.group("qty")
        return {
            "raw": raw_string,
            "quantity": parse_fraction(qty_str),
            "unit": normalize_unit(match.group("unit")),
            "product": match.group("product").strip()
        }
        
    # 2. Test Pattern (Quantité + Produit) (ex: "3 œufs")
    match = PATTERN_QTY_ONLY.search(raw_string)
    if match:
        qty_str = match.group("qty")
        return {
            "raw": raw_string,
            "quantity": parse_fraction(qty_str),
            "unit": None,
            "product": match.group("product").strip()
        }
        
    # 3. Fallback: Pas de quantité détectée (ex: "Sel et poivre")
    return {
        "raw": raw_string,
        "quantity": None,
        "unit": None,
        "product": raw_string
    }
