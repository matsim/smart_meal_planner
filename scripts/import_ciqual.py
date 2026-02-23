import os
import sys
import json
import zipfile
import io
import re
import urllib.request
import xml.etree.ElementTree as ET

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.food import Food

CIQUAL_API_URL = "https://www.data.gouv.fr/api/1/datasets/table-de-composition-nutritionnelle-des-aliments-ciqual/"

TARGET_NUTRIENTS = {
    "energy_kcal": "Energie, Règlement UE N° 1169/2011 (kcal/100 g)",
    "proteins_g": "Protéines, N x facteur de Jones (g/100 g)",
    "carbohydrates_g": "Glucides (g/100 g)",
    "fat_g": "Lipides (g/100 g)",
    "fiber_g": "Fibres alimentaires (g/100 g)",
    "water_g": "Eau (g/100 g)"
}

def clean_value(val: str) -> float:
    if not val or val == '-' or val == 'traces':
        return 0.0
    val = val.replace(',', '.').replace('<', '').strip()
    try:
        return float(val)
    except ValueError:
        return 0.0

def safe_text(node: ET.Element, tag: str) -> str:
    el = node.find(tag)
    return el.text.strip() if el is not None and el.text is not None else ""

def parse_xml_safe(xml_bytes: bytes) -> ET.Element:
    text = xml_bytes.decode('windows-1252', errors='replace')
    # Echapper les < ne faisant pas partie d'une balise valide (incluant <?xml)
    text = re.sub(r'<(?!\/?(?:[a-zA-Z_?]+)(?:>|\s))', '&lt;', text)
    # Echapper les & invalides (non suivis d'une entité connue)
    text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', text)
    text = text.replace('encoding="windows-1252"', 'encoding="utf-8"')
    return ET.fromstring(text.encode('utf-8'))

def import_ciqual():
    print("Recherche de l'URL du fichier CIQUAL (XML)...")
    req = urllib.request.urlopen(CIQUAL_API_URL)
    dataset_info = json.loads(req.read())
    
    zip_url = None
    for res in dataset_info.get("resources", []):
        if 'XML' in res.get('title', '') or 'xml' in res.get('format', '').lower():
            zip_url = res['url']
            break
            
    if not zip_url:
        print("Erreur: Impossible de trouver l'archive XML sur data.gouv.fr")
        return

    print(f"Téléchargement de {zip_url}...")
    req = urllib.request.urlopen(zip_url)
    zip_bytes = req.read()
    print("Extraction en mémoire...")
    
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        alim_file = next(f for f in z.namelist() if f.startswith('alim_') and f.endswith('.xml') and not f.startswith('alim_grp'))
        compo_file = next(f for f in z.namelist() if f.startswith('compo_') and f.endswith('.xml'))
        const_file = next(f for f in z.namelist() if f.startswith('const_') and f.endswith('.xml'))

        print("Analyse des nutriments (const)...")
        const_root = parse_xml_safe(z.open(const_file).read())
        
        # Mape "nom_du_nutriment" -> "const_code"
        nutrient_code_map = {}
        for const in const_root.findall('CONST'):
            code = safe_text(const, 'const_code')
            nom = safe_text(const, 'const_nom_fr')
            for k, target_name in TARGET_NUTRIENTS.items():
                if target_name.lower() in nom.lower():
                    nutrient_code_map[code] = k

        print(f"Codes de nutriments trouvés : {nutrient_code_map}")

        print("Analyse des aliments (alim)...")
        alim_root = parse_xml_safe(z.open(alim_file).read())
        
        foods_dict = {}
        # groupes à exclure : 07 (produits élaborés/plats composés)
        for alim in alim_root.findall('ALIM'):
            code = safe_text(alim, 'alim_code')
            nom = safe_text(alim, 'alim_nom_fr')
            grp_code = safe_text(alim, 'alim_grp_code')
            
            if nom and code and not grp_code.startswith("07"):
                foods_dict[code] = {
                    "name": nom,
                    "energy_kcal": 0.0,
                    "proteins_g": 0.0,
                    "carbohydrates_g": 0.0,
                    "fat_g": 0.0,
                    "fiber_g": 0.0,
                    "water_g": 0.0
                }

        print(f"{len(foods_dict)} aliments bruts retenus (hors plats composés).")

        print("Analyse des compositions (compo)...")
        compo_root = parse_xml_safe(z.open(compo_file).read())
        
        for compo in compo_root.findall('COMPO'):
            alim_code = safe_text(compo, 'alim_code')
            const_code = safe_text(compo, 'const_code')
            teneur = safe_text(compo, 'teneur')
            
            if alim_code in foods_dict and const_code in nutrient_code_map:
                field_name = nutrient_code_map[const_code]
                foods_dict[alim_code][field_name] = clean_value(teneur)

    print("Insertion dans la base de données...")
    db: Session = SessionLocal()
    
    # Récupérer les noms existants pour éviter les doublons
    existing_names = {f[0].lower() for f in db.query(Food.name).all()}
    
    new_foods = []
    for code, data in foods_dict.items():
        if data["name"].lower() not in existing_names:
            food_obj = Food(
                name=data["name"],
                energy_kcal=data["energy_kcal"],
                proteins_g=data["proteins_g"],
                fat_g=data["fat_g"],
                carbohydrates_g=data["carbohydrates_g"],
                fiber_g=data["fiber_g"],
                water_g=data["water_g"],
                is_draft=False
            )
            new_foods.append(food_obj)
            existing_names.add(data["name"].lower())

    if new_foods:
        # Commit par lots pour ne pas exploser la RAM
        batch_size = 500
        for i in range(0, len(new_foods), batch_size):
            db.bulk_save_objects(new_foods[i:i+batch_size])
            db.commit()
            print(f"Inséré lot {i//batch_size + 1}/{(len(new_foods)//batch_size)+1}")
        print(f"Terminé. {len(new_foods)} aliments ajoutés.")
    else:
        print("Aucun nouvel aliment à ajouter.")

if __name__ == "__main__":
    import_ciqual()
