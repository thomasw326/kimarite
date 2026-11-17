# Release UI direction: Heya and Dohyō are separate player phases

Status: **approved product direction; first two-location browser shell implemented on `main`**, with broader UI polish and career integration outstanding. Initially recorded 16 November 2026.
Source: user's release UX discussion.

## Naming and meaning

- **Heya (stable)** is the home/training/management phase. It is for slower, thoughtful decisions that shape the next bout, next block of three, or next tournament. The player should be able to read and compare cards without feeling rushed.
- **Dohyō (sumo ring)** is the bout phase. It is for Tachiai commitment, active turn-by-turn card play, immediate ring state, and the bout result. This is not named "dojo": a *dohyō* is the clay wrestling ring. A heya can contain a practice ring, but these are distinct *gameplay modes*.
- Use both names as clear on-screen locations and modes, not merely a collapsible "Management" panel above a bout on the same continuous page.

## Heya: deliberate management, reading, preparation

The Heya is the default home of the wrestler between matches. It should emphasize:

- The player's created wrestler: name/identity, simple base Power/Technique/Spirit stats, current tournament, career/year progress and record.
- The current 28-card draft and detailed card reading/comparison. Tournament 1 starts with eight standard cards and drafts the other 20. On later tournaments, only the **previous tournament's earned duplicate choices** automatically seed the next 28-card draft (0–12 cards), and the player drafts the rest.
- Upcoming opponents and the next three-bout block, including the existing nine-card allocation (three opening cards per match), inspected card texts and planned strategy.
- Management choices and earned duplication rewards, including choosing which eligible original cards are duplicated and later inherited.
- Tournament results, year-to-date summary across up to six 15-bout tournaments, and the choice to prepare the next tournament when eligible.

Design tone: quieter, readable, organized; slower pacing, ample room for explanations and card inspection, with a deliberate and legible **Enter the Dohyō / Begin Bout** action. No combat input controls should be present in this mode.

## Dohyō: focused moment-to-moment wrestling

The Dohyō occupies a visually and functionally distinct combat layout:

- The clay ring and Position track should reflect the actual game state, including the ±4 boundary and ring-out risks.
- At the beginning of the bout, resolve the player's own preselected opening and interactive Tachiai decision, **without revealing the opponent's Tachiai cards before the player commits**.
- Prominently display the hand and relevant choices, Push/Position, Momentum, Power, Grip, remaining Plays, current Kimarite and Temporaries.
- Show the result and the reason for the victory or defeat. Offer a clear **Return to Heya** action following the bout.
- Keep the phase responsive and readable on small screens. Detailed rule inspection remains available but should not clutter the primary combat flow.

Design tone: focused, high-contrast, immediate and dramatic; no drafting, rewards or opponent scouting controls in the primary combat surface.

## Recommended transition contract

1. **New wrestler -> Heya:** enter simple stat creation and initial 28-card draft. Do not force selection of a prebuilt B9/B10 wrestler.
2. **Heya planning -> Dohyō:** for each block of three bouts, inspect the next opponents, allocate nine cards (three per bout), then commit to begin the selected bout.
3. **Dohyō opening -> Exchange:** interactive player Tachiai and then the live card-game fight. Keep private opponent choices hidden until permitted by rules.
4. **Dohyō bout finished -> Heya:** present the bout result and return to the stable. Show match record and preparation for the upcoming bout, even if there are no new management decisions.
5. **After each three-bout block -> Heya rewards:** resolve any eligible duplication rewards and the next block's card allocation before returning to the ring. Do not place this reading-heavy management inside the combat HUD.
6. **After each 15-bout tournament -> Heya:** show tournament summary, earned duplicate cards, and begin the next tournament's fresh draft, up to the sixth tournament/year end.
7. **After tournament six -> Heya year summary** (future implementation): full-year record and ending.

Between-bout returns should be easy to pass through when the player has no new decisions, without requiring arbitrary extra clicks or repeatedly showing a full tutorial. These are **state transitions**, not free navigation that can discard/rewind an active bout.

## Release acceptance criteria

- Players can immediately distinguish Heya and Dohyō by title, layout, visible actions, and look/feel.
- Heya is the only place for wrestler stats, draft, reward selection, opponent/block planning, and between-tournament progression.
- Dohyō is the only place for Tachiai commitment, turn actions and the immediate match result.
- The interface never shows both phases' action controls together as a stacked development test page.
- A completed bout returns to Heya with the result and relevant next action preserved. The player cannot accidentally lose an in-progress bout by navigating.
- The release works with the draft-created human wrestler, not a requirement to pick one of 26 legacy named wrestlers or all 60 AI framework decks.
- Saving/resuming recovers the correct phase and pending decisions.

## Current gap

**Implemented in the first browser pass:** `web/index.html` now has separate `#heya-view` and `#dohyo-view` shells; CSS gives them different visual identities and keeps inactive controls hidden. `web/client.js` switches into the Dohyō for Tachiai/Exchange, only allows return after a finished bout, and restores the Heya location for already-returned completed bouts. The old automatic next-bout action was replaced with an explicit return to the Heya, where subsequent management decisions are made. Phase-specific tests cover location switching and saved-phase behavior.

**Also implemented in the ring UI:** The `#dohyo-ring` wrestler markers now shift with the authoritative shared Position value (−4 through +4). Their movement and an explicit edge-danger highlight are visible during live combat; ±4 stays within the ring, while a further Push causes ring-out according to the unchanged rules. Pending Tachiai still hides the opposing opening/Position until it is committed. Regression coverage checks all Position extremes, hidden-opening state and accessibility labels.

**Created-wrestler integration:** The default Heya setup now contains a separate wrestler-name input and basic stat allocation; the drafted identity flows through the backend B11 opening and live Human-vs-AI engine without selecting one of the legacy wrestler templates. The existing B9 wrestler/classic controls have been moved under closed developer practice options. AI opponents continue to use approved roster-based style proxies. Saved tournament/draft state retains the chosen human name.

**Year and local save implementation:** Each tournament now carries prior tournament summaries and the same created wrestler identity/stats into its next 28-card draft. The Heya and tournament results display cumulative year scores and individual tournament scores, and the sixth tournament ends the year (90 bouts maximum). The browser retains management, draft and bout recovery state in local browser storage as well as session storage, and clears obsolete finished bout state when starting a new draft/block. This is a local single-player save, not a cloud account or public multiuser persistence.

**Year-end replay:** After completing the sixth tournament, Heya offers **Start a new wrestler**. The player is warned that this replaces their locally stored year and must explicitly confirm. Results can be copied before starting fresh. No seventh tournament is allowed in the same year.

**Still outstanding:** detailed visual/UX polish, explicit design for ending a year early, verified manual end-to-end/cross-device save/resume QA, and public hosting hardening. The underlying battle engine, draft selection and AI were intentionally not changed.

Project roadmap:
https://docs.google.com/spreadsheets/d/1YCAG7skE06kPsjadfWr_L7CYDCK_G2HJ68GcvadZcLk/edit
