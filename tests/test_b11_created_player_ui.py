"""Created wrestler is primary; old B9 preset selectors remain optional QA tools."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web"
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "client.js").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        vals = dict(attrs)
        if "id" in vals:
            self.elements[vals["id"]] = (tag, vals, tuple(self.tags))
        if tag == "details":
            self.tags.append(("details", vals.get("id")))

    def handle_endtag(self, tag):
        if tag == "details" and self.tags:
            self.tags.pop()


def test_player_name_is_primary_form_control_and_preset_is_not_required():
    parser = Structure()
    parser.feed(HTML)
    assert parser.elements["wrestler-name"][0] == "input"
    attrs = parser.elements["wrestler-name"][1]
    assert attrs["type"] == "text"
    assert attrs["maxlength"] == "32"
    assert attrs["value"] == "Your Rikishi"
    assert "Developer practice options" not in HTML
    assert "legacy-management-options" not in parser.elements
    assert '<div hidden><select id="management-deck">' in HTML


def test_standard_draft_uses_created_name_and_stats_independently_of_legacy_roster():
    assert "const draftedName=$('wrestler-name').value.trim()" in JS
    assert "const human=standard?(continuing?management.human:draftedName):$('management-deck').value" in JS
    assert "const created=previous?.created_stats||creationChoices()" in JS
    assert "activeDraft={human,seed,world_seed:" in JS
    assert "created_stats:created,tournament_history,starting_cards:[...starting]" in JS
    assert "management={human:d.human,seed:d.seed,opening_mode:'b11_live',created_stats:d.created_stats" in JS
    assert "request.created_stats=m.created_stats" in JS
    assert "request.starting_cards=m.starting_cards" in JS
    assert "request.draft_picks=m.draft_picks" in JS


def test_created_identity_survives_resume_and_next_tournament_draft():
    assert "$('wrestler-name').value=saved.human" in JS
    assert "$('wrestler-name').value=pending.human" in JS
    assert "continuing?management.human:draftedName" in JS
    assert "const previous=continuing?management:null" in JS
    assert "previous.next_starting_cards??earnedNextStartingCards(previous)" in JS
    assert "management.next_starting_cards=earnedNextStartingCards(management)" in JS
    # The legacy practice dropdown is still available; standard created
    # wrestlers instead draw 15 nonrepeating opponents from the 42-place league.
    assert "const roster=[...$('opponent').options]" in JS
    assert "opponents:Array(15).fill(null),b12_opponent_ids:Array(15).fill(null)" in JS
    assert "assignB12Block(management,division)" in JS
    assert "division_roster:division.roster" in JS
