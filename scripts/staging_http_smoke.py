"""Check a deployed preview using only public browser APIs.

Usage: python scripts/staging_http_smoke.py --url https://...onrender.com
No private game information or account credentials are needed.
"""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


STARTERS = [
    "Yorikiri", "Oshidashi", "Oshi", "Tsuki",
    "Gain Left Grip", "Gain Right Grip", "Give Ground", "Sonkyo",
]


def fetch(base: str, path: str, data: dict | None = None):
    request = Request(
        base.rstrip("/") + path,
        headers={"Content-Type": "application/json", "User-Agent": "kimarite-staging-smoke/1"},
        data=json.dumps(data).encode() if data is not None else None,
        method="POST" if data is not None else "GET",
    )
    with urlopen(request, timeout=65) as response:
        body = response.read(1_000_000)
        if response.status not in (200, 201):
            raise RuntimeError(f"{path} returned {response.status}")
        if path == "/":
            return body.decode("utf-8")
        return json.loads(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://kimarite-b12-alpha-preview.onrender.com")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("Staging URL must use HTTPS.")

    # Free preview instances can take a while to wake. Wait for the actual
    # current draft-first UI, not merely any HTTP 200 HTML response.
    for attempt in range(10):
        try:
            page = fetch(base, "/")
            if all(f'id="{item}"' in page for item in
                   ("wrestler-name", "heya-view", "dohyo-view", "year-record")):
                break
            raise RuntimeError("Hosted UI lacks the current player-created wrestler flow.")
        except (HTTPError, URLError, RuntimeError) as exc:
            if attempt == 9:
                raise RuntimeError(f"Staging never became ready: {exc}") from exc
            print(f"Preview not ready (attempt {attempt+1}/10): {exc}", flush=True)
            time.sleep(15)
    roster = fetch(base, "/api/roster")["roster"]
    if len(roster) < 15 or "The Technician" not in roster:
        raise AssertionError("AI opponent roster unavailable.")
    catalogue = fetch(base, "/api/b11/draft/catalogue", {})
    if len(catalogue["kimarite_names"]) < 3:
        raise AssertionError("Kimarite catalogue incomplete.")

    seed = 20261117
    picks = []
    for i in range(20):
        offer = fetch(base, "/api/b11/draft/offer", {
            "starting_cards": STARTERS, "picks": picks, "seed": seed,
        })["choices"]
        names = [card["name"] for card in offer]
        if len(names) != 3 or len(set(names)) != 3:
            raise AssertionError(f"Draft offer {i+1} was not three distinct cards.")
        if any(name in (*STARTERS, *picks) for name in names):
            raise AssertionError(f"Draft offer {i+1} offered a previously owned card.")
        picks.append(names[0])
    deck = fetch(base, "/api/b11/draft/deal", {
        "starting_cards": STARTERS, "picks": picks,
        "draft_seed": seed, "seed": seed,
    })
    if deck["deck_size"] != 28 or len(deck["cards"]) != 9:
        raise AssertionError("The first nine-card deal did not come from a 28-card draft.")

    started = fetch(base, "/api/session", {
        "human": "Staging Test Rikishi", "opponent": "The Technician",
        "seed": seed, "opening_mode": "b11_live",
        "opening_cards": STARTERS[:3],
        "starting_cards": STARTERS, "draft_picks": picks,
        "draft_seed": seed, "duplicated_indices": [],
        "created_stats": {"power": 2, "technique": 1, "spirit": 0},
    })
    pending = started["state"]
    if pending["phase"] != "choose_tachiai" or pending["opening"] is not None:
        raise AssertionError("Player-controlled hidden Tachiai phase was not created.")
    if pending["human"]["name"] != "Staging Test Rikishi":
        raise AssertionError("Custom wrestler identity lost before the bout.")
    if "cards" in pending["opponent"]:
        raise AssertionError("Opponent's hidden Tachiai cards were exposed.")

    committed = fetch(base, "/api/session/" + started["token"] + "/action", {
        "type": "commit_tachiai", "indices": [0],
    })
    state = committed["state"]
    if state["human"]["name"] != "Staging Test Rikishi":
        raise AssertionError("Custom player identity lost entering live combat.")
    if state["opening"]["human"]["base_stats"] != [2, 1, 0]:
        raise AssertionError("Created wrestler's base stats were not preserved.")
    print("STAGING_SMOKE_OK: page, roster, 20 draft offers, 28-card deal, "
          "custom wrestler, hidden Tachiai and live bout handoff", flush=True)


if __name__ == "__main__":
    main()
