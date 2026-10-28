"""Guard against the tournament progress desynchronization reported after bout two.

The browser owns tournament sessionStorage; these checks ensure that a finished
standalone bout cannot be counted, next-bout errors roll back the round, and
the nine-card reallocation doesn't erase earlier results.
"""
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1] / "web" / "client.js"


def test_finished_bout_is_bound_to_tournament_identity():
    source = CLIENT.read_text()
    assert "sessionSetup={...request,tournament_bout:i}" in source
    assert "activeTournamentBout()===m.round&&m.results.length===m.round" in source
    assert "m.results.push(" in source
    assert "sessionSetup.seed===m.seed+m.round+1" in source


def test_next_bout_requires_recorded_result_and_rolls_back_failed_advance():
    source = CLIENT.read_text()
    assert "m.results.length!==m.round+1" in source
    assert "m.round--;managementSave()" in source
    assert "Could not start next bout:" in source
    assert "Could not deal the next round:" in source


def test_pending_tachiai_clears_previous_bout_continue_button():
    source = CLIENT.read_text()
    pending = source.split("function renderPendingTachiai(g){", 1)[1].split("function render(", 1)[0]
    assert "if(management)managementStatus()" in pending
    assert "$('management-next').hidden=!" in source


def test_optional_individual_bout_and_decorative_ring_collapsed_by_default():
    from html.parser import HTMLParser

    html = (CLIENT.parent / "index.html").read_text()
    css = (CLIENT.parent / "style.css").read_text()

    class Check(HTMLParser):
        def __init__(self):
            super().__init__()
            self.details = {}
            self.ids = set()
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if "id" in a:
                self.ids.add(a["id"])
            if tag == "details" and a.get("id") in ("single-bout-details", "dohyo-details"):
                self.details[a["id"]] = "open" in a

    parsed = Check()
    parsed.feed(html)
    assert parsed.details == {"single-bout-details": False, "dohyo-details": False}
    assert {"human", "opponent", "start", "management-deal", "management-board", "round", "tracks"} <= parsed.ids
    assert ".setup-fields{display:grid" in css
    assert '<div id="tracks" class="tracks"></div></section>' in html


def test_mobile_live_bout_hud_keeps_position_momentum_and_opponent_effects_visible():
    html = (CLIENT.parent / "index.html").read_text()
    css = (CLIENT.parent / "style.css").read_text()
    js = CLIENT.read_text()
    assert 'id="bout-hud"' in html and 'aria-label="Live bout status"' in html
    assert all(f'id="hud-{label}"' in html for label in ["turn", "position", "momentum", "opponent", "effects"])
    assert ".bout-hud{position:sticky;top:0" in css
    assert ".bout-hud[hidden]{display:none!important}" in css
    assert "@media (min-width:720px){.bout-hud{display:none}}" in css
    assert "renderBoutHud(g);game=g;" in js
    assert "renderBoutHud(g);\n game=g;" in js
    assert "g.position===undefined||g.momentum===undefined" in js
    assert "foe.temporary||[]" in js and "foe.kimarite||[]" in js
    assert "zoneEffect(c,zone)" in js
    assert "Opponent effects: none active" in js
