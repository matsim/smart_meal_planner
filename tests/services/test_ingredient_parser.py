import pytest
from app.services.ingredient_parser import parse_ingredient

def test_parse_simple_ingredient():
    res = parse_ingredient("3 tomates")
    assert res["quantity"] == 3.0
    assert res["unit"] is None
    assert res["product"] == "tomates"

def test_parse_gousses_ail():
    res = parse_ingredient("2 gousses d'ail finement hâchées")
    assert res["quantity"] == 2.0
    assert res["unit"] == "Gousses"
    assert res["product"] == "ail finement hâchées"

def test_parse_gingembre():
    res = parse_ingredient("4 gingembre finement hâchée")
    assert res["quantity"] == 4.0
    assert res["unit"] is None
    assert res["product"] == "gingembre finement hâchée"

def test_parse_grammes_boeuf():
    res = parse_ingredient("400 g de boeuf coupé en lanières")
    assert res["quantity"] == 400.0
    assert res["unit"] == "g"
    assert res["product"] == "boeuf coupé en lanières"

def test_parse_cuilleres_typo():
    # Test avec faute de frappe "cuilère"
    res = parse_ingredient("4 cuilère à soupe de sauce soja")
    assert res["quantity"] == 4.0
    assert res["unit"] == "c.à.s"
    assert res["product"] == "sauce soja"

def test_parse_fraction():
    res = parse_ingredient("1/2 tasse de sucre")
    assert res["quantity"] == 0.5
    assert res["unit"] == "Tasse"
    assert res["product"] == "sucre"

def test_parse_decimal():
    res = parse_ingredient("1.5 kg de farine")
    assert res["quantity"] == 1.5
    assert res["unit"] == "kg"
    assert res["product"] == "farine"

def test_parse_no_qty():
    res = parse_ingredient("Sel et poivre au goût")
    assert res["quantity"] is None
    assert res["unit"] is None
    assert res["product"] == "Sel et poivre au goût"

def test_parse_cuilleres_cafe():
    res = parse_ingredient("2 cuillères à café de maïzena")
    assert res["quantity"] == 2.0
    assert res["unit"] == "c.à.c"
    assert res["product"] == "maïzena"
