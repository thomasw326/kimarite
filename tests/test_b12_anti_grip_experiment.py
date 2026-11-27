from kimarite.catalog import card_by_name

def test_ottsuke_orbs():
    c = card_by_name("Ottsuke")
    assert (c.power, c.technique, c.spirit) == (1, 1, 1)
