from app.services.ingredient_parser import parse_ingredient

tests = [
    "4 cuillères à soupe de sauce soja",
    "1.5 kg de pommes de terre",
    "1/2 tasse d'eau",
    "Sel et poivre",
    "3 oeufs",
    "200g de farine",
    "1 pincée de sel"
]

for t in tests:
    print(repr(t), "->", parse_ingredient(t))
