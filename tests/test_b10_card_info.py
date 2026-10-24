"""Audit completeness of UI descriptions without changing game mechanics."""
from kimarite.catalog import card_by_name
from kimarite.b10_card_info import card_info, CARD_TEXT, GLOSSARY
from kimarite.b10_human_session import roster, public_snapshot, new_b10_session
import json
from pathlib import Path


def test_no_unverified_card_text_is_passed_off_as_approved():
    deck_data=json.loads((Path(__file__).resolve().parents[1]/"data"/"b9_30_wrestler_decks.json").read_text())["decks"]
    all_names={name for wrestler in roster() for name in deck_data[wrestler]["cards"]}
    for name in all_names:
        card=card_info(card_by_name(name))
        if card["description_status"]=="verified":
            assert card["description"]
            assert name in CARD_TEXT
        else:
            assert card["description_status"]=="needs_audit"
            assert card["description"]==""
    assert {"Pull","Give Ground","Katasukashi"} <= set(CARD_TEXT)


def test_ui_snapshot_offers_glossary_and_audit_state():
    session=new_b10_session("Arm Controller","The Technician",seed=42)
    snapshot=public_snapshot(session)
    assert snapshot["glossary"]["Momentum"]
    cards=snapshot["selection"]["options"] if snapshot["selection"] else snapshot["human"]["hand"]
    for card in cards:
        assert card["description_status"] in ("verified","needs_audit")
        assert "description" in card
