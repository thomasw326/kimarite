# B12 alpha preview — operations and limits

Updated: 17 November 2026. **Development preview, not a production-ready itch.io release.**

## Verified deployment

- URL: https://kimarite-b12-alpha-preview.onrender.com
- Render service: `kimarite-b12-alpha-preview` (`srv-dbuaro2fngtc73e9bffg`)
- Source: `thomasw326/kimarite`, `main` branch, auto-deploy on commits
- Region: Oregon; **free** Render web service plan; Docker runtime
- Startup: `Dockerfile` runs `python -m kimarite.b10_web`, listening on `0.0.0.0:$PORT`
- UI and API use the **same origin**, with UI `/` and game endpoints under `/api/`.
- First Render deploy `dep-dbuaroafngtc73e9bg30` reported **live**. Render logs showed HTTP GET `/` 200.
- Hosted functional smoke succeeded in GitHub Actions [run 44161789176](https://github.com/thomasw326/kimarite/actions/runs/44161789176), verifying 20 card offers, 28-card draft, AI opponent roster, created wrestler name/stats, pre-commit hidden Tachiai, and live combat handoff.
- Same-commit full code tests [run 44161789168](https://github.com/thomasw326/kimarite/actions/runs/44161789168) succeeded.

This provides a direct development playtest URL without changing the previous B10/B11 playtest services.

## Important current limitations

1. **Server data is ephemeral.** `src/kimarite/b10_web.py` keeps live bout sessions in a process-local dictionary. A restart or replacement instance loses those session tokens. Browser save/replay stores setup and accepted commands locally and can attempt reconstruction, but real-world recovery under interruptions needs manual QA.
2. **No production multi-user hardening yet.** The server uses `ThreadingHTTPServer` and caps active session entries at 100; it does not currently have robust session expiry, cleanup, request throttling, authentication, or per-user quotas. Concurrent browser sessions use distinct random tokens but capacity and denial-of-service resistance have not been validated. Public browsing is for development QA only.
3. **Local saves.** The browser writes `sessionStorage` and `localStorage`, not cloud data. Saves are browser- and device-local; private browsing/storage clearing can delete them. Browser recovery is not equivalent to persistent server storage.
4. **Free plan constraints.** Idle startup delays and resource limits are possible; availability is not promised. The preview is not guaranteed to be continuously available. Review Render account billing/usage before selecting an eventual production plan.
5. **Bounded simulation, not full UI QA.** Automated tests validate draft logic, live session handoff, year summary and local storage helpers; an entire 15-bout tournament and full six-tournament run have **not** yet been manually played on the deployed UI.
6. **Legacy AI fixtures.** The browser still draws opponents from the old 26-name roster, representing existing approved AI style proxies. The 60 B12 AI frameworks are simulation/test data and not player-selectable characters.
7. **Release options outstanding.** Itch.io launch method, production hardening, visual/mobile polish, optional early-year ending, and full browser save/restore QA remain open.

## How to check and diagnose

1. Open the preview URL and confirm the Heya shows a custom wrestler-name field, 2/1/0 stat setup, and 28-card draft.
2. Run the automated hosted check from GitHub Actions workflow `staging-http-smoke` or via `python scripts/staging_http_smoke.py --url https://kimarite-b12-alpha-preview.onrender.com` on a network-enabled machine.
3. If the site is down, inspect Render's `kimarite-b12-alpha-preview` latest deploy status and service logs. Check for Docker build errors, port binding, server restarts, or free-plan suspensions.
4. If a bout expires, browser replay may reconstruct from accepted actions; preserve the seed and copied game log when investigating. Do not assume the browser save repairs every server-side interruption.
5. Keep gameplay changes on latest approved `main`; do not restore the previous B11/B10 playtest branches as a gameplay baseline.

## Release gates

**Before calling it a public alpha**, require secure multi-user session handling/capacity tests, a proper end-to-end full tournament and six-tournament smoke, browser/mobile QA, a repeatable new-player tutorial/checklist, production or clearly-scoped alpha operating expectations, and itch.io release setup. The preview alone does not satisfy those release gates.
