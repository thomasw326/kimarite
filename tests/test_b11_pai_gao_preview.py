"""B11 Pai Gao previews track the live 2/1/0 style allocation."""
import ast
import re
from pathlib import Path

from kimarite.b10_human_session import STYLE_PROXIES, roster
from kimarite.styles_v5 import STYLES


def js_map(source, name):
    pattern = r"const " + name + r"=\{(.*?)\};"
    match = re.search(pattern, source, re.S)
    assert match, name
    return ast.literal_eval("{" + match.group(1) + "}")


def test_pai_gao_style_map_matches_live_b11_base_stats():
    source = (Path(__file__).resolve().parents[1] / "web" / "client.js").read_text()
    styles = js_map(source, "B11_BASE_STYLES")
    proxies = js_map(source, "B11_BASE_PROXIES")
    for name in roster():
        style = STYLES[STYLE_PROXIES.get(name, name)]
        assert proxies.get(name, name) == STYLE_PROXIES.get(name, name)
        actual = styles[proxies.get(name, name)].split(",")
        assert actual == [style.primary.lower(), style.secondary.lower()]


def test_pai_gao_preview_adds_base_three_cards_and_universal_one():
    source = (Path(__file__).resolve().parents[1] / "web" / "client.js").read_text()
    assert "base[order[0]]=2;base[order[1]]=1" in source
    assert "base[k]+1+orbs[i]" in source
    assert "box.append(b11TachiaiPreview(management,i))" in source
    assert "Before Oshi/Tsuki reveal-chain bonuses" in source
