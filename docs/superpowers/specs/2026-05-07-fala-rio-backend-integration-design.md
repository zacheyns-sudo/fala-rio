# Fala Rio Backend Integration Design

Date: 2026-05-07

## Goal

Add the Flask backend described in `CODEX.md` and wire the existing single-file frontend to use it for AI tutor turns, translation grading, state sync, and API key persistence.

## Scope

This is a focused backend integration slice. It creates `app.py`, `requirements.txt`, `Procfile`, and `data/vocab.json`, then updates only the existing frontend surfaces that are marked for backend wiring:

- speaking practice microphone turn submission
- translation test grading
- tutor speech playback

The existing visual layout and navigation stay intact.

## Backend Design

`app.py` exposes four API routes:

- `POST /api/tutor` streams a Claude tutor response as plain text.
- `POST /api/check-translation` asks Claude to grade an English translation and returns JSON.
- `GET /api/state` returns `state/user.json`, or `{}` when no saved state exists.
- `POST /api/state` writes the posted state to `state/user.json`.
- `POST /api/config` stores an API key in the Flask session.

API keys are resolved in this order: `X-API-Key` request header, `flask.session["api_key"]`, then `ANTHROPIC_API_KEY`. Missing keys return a clear JSON error for non-streaming routes and a plain streamed error for the tutor route.

The tutor route uses `claude-sonnet-4-6`, Anthropic streaming, and an ephemeral cached system prompt block. The route streams raw text chunks so the frontend can split the Portuguese reply from the metadata block using `<<<META>>>`.

## Frontend Design

The speaking state gains a live `messages` array, latest tutor text, correction tip, vocab pills, busy/error fields, and turn count. Picking a scenario initializes the conversation with a first tutor greeting.

`toggleMic()` starts browser speech recognition in `pt-BR`. When a final transcript arrives, the app appends a user bubble, posts the turn to `/api/tutor`, reads the streaming response, splits on `<<<META>>>`, appends the tutor bubble, updates the tutor card, speaks the Portuguese reply, and saves progress.

The tutor card's Replay and Slower buttons use `speechSynthesis` with `lang: "pt-BR"` and a slower rate for the second button.

`checkTranslate()` posts the current Portuguese prompt and the typed English answer to `/api/check-translation`. It uses the backend's `correct` value for scoring and displays backend feedback when available.

## Data

`data/vocab.json` contains at least 40 Week 1 Food & Groceries entries. Entries use the shape requested by `CODEX.md`: `id`, `pt`, `en`, `phonetic`, `category`, `example_pt`, `example_en`, `due`, `interval`, and `times_seen`.

## Error Handling

Frontend errors are visible but small: speaking errors appear in the tutor tip area, and translation grading falls back to a wrong result with feedback if the backend is unavailable. Backend JSON parsing and model responses are guarded so malformed model JSON returns a useful response instead of crashing.

## Testing

Backend tests cover:

- state file creation and round-trip behavior
- API key priority
- config session storage
- translation grading with a fake Anthropic client
- tutor streaming with a fake Anthropic stream
- missing API key behavior

Frontend wiring is checked with lightweight text assertions for the new TODO replacements and by serving the app locally enough to verify the Flask app imports and routes are available.
