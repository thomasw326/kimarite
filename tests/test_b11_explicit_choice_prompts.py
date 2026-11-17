"""Every live card choice identifies its consequence before the player selects.

This is UI metadata only. The indices and options sent to the game engine must
remain identical, and opponent hidden hand identities must never be exposed.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from kimarite.b10_human_session import new_b10_session
from kimarite.b10_web import labelled_choices
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


@pytest.fixture
def bout():
    return new_b10_session("Arm Controller", "The Technician", seed=42)


def test_oshi_requires_player_to_discard_not_play_another_card(bout):
    own = bout.state.fighter(bout.human_side)
    own.hand = [card_by_name("Oshi"), card_by_name("Tsuki"), card_by_name("Shove")]
    prompt = labelled_choices(bout, ChoiceRequired("Oshi", "hand_index", [0, 1]),
                             {"hand_index": 0})
    assert "DISCARD" in prompt["choice_title"]
    assert prompt["choice_verb"] == "Discard"
    assert "not playing" in prompt["choice_help"]
    assert [o["value"] for o in prompt["options"]] == [0, 1]
    assert [o["card"]["name"] for o in prompt["options"]] == ["Tsuki", "Shove"]


@pytest.mark.parametrize("card,key,options,verb,word", [
    ("Pull", "hand_index", [0], "Discard", "DISCARD"),
    ("Tsukitaoshi", "hand_index", [0], "Discard", "DISCARD"),
    ("Kotenage", "hand_index", [0], "Discard", "DISCARD"),
    ("Uwatedashinage", "hand_index", [0], "Discard", "DISCARD"),
    ("Katasukashi", "discard_index", [0], "Recover", "RETURN"),
    ("Inashi", "discard_index", [0], "Recover", "RETURN"),
    ("Power Water", "discard_index", [0], "Recover", "RETURN"),
    ("Headlong Charge", "sacrifice_kimarite", [0], "Sacrifice", "REMOVE"),
    ("Big Tsuki", "temporary_index", [0], "Remove", "REMOVE"),
    ("Uwate", "uwate_card_index", [0], "Play", "PLAY"),
    ("Hikiotoshi", "hikiotoshi_card_index", [0], "Keep", "KEEP"),
    ("Utchari", "utchari_card_index", [0], "Keep", "KEEP"),
    ("Tottari", "opponent_deck_index", [0], "Discard", "DISCARD"),
    ("Hatakikomi", "opponent_hand_index", [0], "Discard", "DISCARD"),
    ("Ottsuke", "card_target", [0], "Remove", "REMOVE"),
    ("Tsuki", "grip", ["left", "right"], "Reduce", "REDUCE"),
    ("Tsuriotoshi", "mode", ["power", "momentum"], "Use", "effect"),
    ("Hatakikomi", "use_optional", [True, False], "Choose", "optional"),
    ("Kotenage", "cycle_if_no_grip", [True, False], "Choose", "discard"),
    ("Uwatedashinage", "discard_for_grip", [True, False], "Choose", "Left Grip"),
    ("Shitatehineri", "replay_discard_index", [0], "Play & Exhaust", "Exhaust"),
    ("Shitatehineri", "replay_discard_index_1", [0], "Play & Exhaust", "Exhaust"),
])
def test_choice_prompts_explicitly_name_effect(bout, card, key, options, verb, word):
    result = labelled_choices(bout, ChoiceRequired(card, key, options))
    assert result["choice_verb"] == verb
    assert word.lower() in (result["choice_title"] + " " + result["choice_help"]).lower()
    assert [o["value"] for o in result["options"]] == options


def test_hatakikomi_optional_effect_spells_out_tradeoff(bout):
    prompt = labelled_choices(bout, ChoiceRequired("Hatakikomi", "use_optional", [True, False]))
    assert "lose 1 Momentum" in prompt["choice_help"]
    assert "opponent" in prompt["choice_help"]
    assert [o["label"] for o in prompt["options"]] == ["Yes", "No"]


def test_opponent_hidden_cards_are_never_revealed_by_more_descriptive_prompt(bout):
    foe = bout.state.opponent(bout.human_side)
    foe.hand = [card_by_name("Oshi"), card_by_name("Yori")]
    prompt = labelled_choices(
        bout, ChoiceRequired("Hatakikomi", "opponent_hand_index", [0, 1])
    )
    assert prompt["choice_verb"] == "Discard"
    assert [o["value"] for o in prompt["options"]] == [0, 1]
    assert all("card" not in o for o in prompt["options"])
    assert all("hidden" in o["label"] for o in prompt["options"])
    assert "Oshi" not in json.dumps(prompt) and "Yori" not in json.dumps(prompt)


def run_browser_choice(prompt):
    node_exe = shutil.which("node")
    if node_exe is None:
        pytest.skip("Node is needed to run the browser selection prompt")
    body = "function choicePrompt(detail){" + JS.split(
        "function choicePrompt(detail){", 1
    )[1].split("async function loadOpening()", 1)[0]
    stub = r"""
const root={};
function node(tag,cls,text){
 const n={tag,className:cls||'',textContent:text||'',children:[],attributes:{},
 append(...items){this.children.push(...items)},
 replaceChildren(...items){this.children=[...items]},
 setAttribute(k,v){this.attributes[k]=v},
 scrollIntoView(){}};
 return n;
}
function btn(text,fn,cls){const b=node('button',cls,text);b.onclick=fn;return b}
function $(name){return root[name] ||= node('section',name)}
function displayCardName(name){return name==='Oshi'?'Push':name}
let pendingPlay={type:'play_card',choices:{}};
const actions=[];
function act(cmd){actions.push(JSON.parse(JSON.stringify(cmd)))}
function inspect(){}
"""
    script = stub + body + r"""
const prompt=JSON.parse(process.argv[1]);
choicePrompt(prompt);
const panel=$('choices');
const strip=panel.children.find(c=>c.className==='cards');
const firstButton=strip.children[0].children[0];
firstButton.onclick();
console.log(JSON.stringify({
 heading:panel.children[0].textContent,
 help:panel.children[1].textContent,
 verb:firstButton.children[0].textContent,
 target:firstButton.children[1].textContent,
 aria:firstButton.attributes['aria-label'],
 action:actions[0],
 cardCount:strip.children.length,
 inspectButton:strip.children[0].children[1]?.textContent||''
}));
"""
    result = subprocess.run(
        [node_exe, "-e", script, json.dumps(prompt)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_browser_shows_discard_instruction_on_oshi_card_choice(bout):
    own = bout.state.fighter(bout.human_side)
    own.hand = [card_by_name("Oshi"), card_by_name("Tsuki"), card_by_name("Shove")]
    prompt = labelled_choices(bout, ChoiceRequired("Oshi", "hand_index", [0, 1]),
                             {"hand_index": 0})
    result = run_browser_choice(prompt)
    assert result["heading"].startswith("Push — Choose 1 card to DISCARD")
    assert "DISCARD" in result["help"]
    assert result["verb"] == "Discard"
    assert result["target"] == "Tsuki"
    assert result["aria"] == "Discard: Tsuki"
    assert result["action"]["choices"] == {"hand_index": 0}
    assert result["cardCount"] == 2
    assert result["inspectButton"] == "Inspect Tsuki"


def test_action_verb_is_readable_with_small_screen_choice_layout():
    assert "#choices .choice-help" in CSS
    assert "#choices .choice-action-verb" in CSS
    assert "#choices .choice-action-target" in CSS
    assert "aria-label" in JS.split("function choicePrompt(detail){", 1)[1].split(
        "async function loadOpening()", 1
    )[0]
