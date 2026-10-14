---
name: orca-browser-check
description: Check this project's web UI (Next.js on :3000) and external pages such as TradingView or set.or.th in Orca's embedded browser, avoiding the known Orca CLI quirks. Use when a task says to open, look at or verify a page, e.g. the candidate list, a stock detail page or a TradingView CDC value.
---

# Orca browser check

Generic commands are in the bundled `orca-cli` skill. This skill covers what goes wrong in *this* project, so it doesn't get rediscovered each session.

## Start the app

```bash
cd engine && uv run uvicorn shortlist.api:app --port 8000   # terminal 1
cd web && bun run dev                                        # terminal 2, http://localhost:3000
```

Pages: `/` (candidate list, run-batch button, failed-stock list) and `/stock/<SYMBOL>` (gates, fair value panel and tooltips, CDC, RRR, events).

## Quirks

| Do | Don't | Why |
|---|---|---|
| `orca tab create --url <url>` for every page | `orca goto` | After `goto`, `snapshot` and `eval` only see the Next.js PPR shell, not the streamed content |
| Use `orca screenshot` as ground truth, then read the image | Trust `snapshot` text alone | Same PPR issue, and snapshot can lag behind the rendered page |
| Poll with a short `orca wait --timeout <ms>` plus a screenshot | `orca wait --text ...` | `--text` can hang with no timeout |
| Type dates with one `orca keypress --key <digit>` per digit after clicking the field | `orca fill` on `<input type="date">` | Date inputs ignore `fill` |
| Close tabs you created with `orca tab close --page <id>` | Leave tabs open | Later commands act on the active tab |

## Steps

1. `orca status`. If the runtime isn't reachable, run `orca open`.
2. `orca tab create --url http://localhost:3000/stock/SCAP --json` and keep the page id.
3. `orca screenshot --page <id>` and read the image. Hover for tooltips with `snapshot` → `click`/`scrollintoview` on the ref, then take another screenshot.
4. For TradingView, set CDC ActionZone V3 2020 to `close 12 26 1` and read Fast/Slow from the data window in the screenshot. If it asks for a login, stop and ask the user to log in inside the Orca tab.
5. Report what the screenshot shows, with values copied exactly. Don't infer values from the code.
