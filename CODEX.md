# Fala Rio — Backend Brief for Codex

## What this is

A Brazilian Portuguese language learning app. Single-file frontend (`index.html`) — all UI, state, and SRS logic lives there. Codex owns the Flask backend only.

## Files to create

```
app.py
data/vocab.json
Procfile
requirements.txt
```

---

## app.py

Flask app. Four routes.

### POST /api/tutor

The core voice-to-voice AI tutor turn.

**Request:**
```json
{
  "history":  [{"role": "user", "content": "Eu quero um café"}],
  "message":  "Não, só isso. Quanto é?",
  "scenario": "cafe",
  "turn":     3
}
```

**Behaviour:**
- Read API key from `X-API-Key` header first; fall back to `ANTHROPIC_API_KEY` env var.
- Call `claude-sonnet-4-6` with streaming enabled.
- System prompt (cache with `cache_control: ephemeral`):

```
You are a Brazilian Portuguese conversation tutor running a scenario called "{scenario}".
Reply ONLY in Brazilian Portuguese — 1–2 short sentences, conversational and natural.
Use Carioca (Rio de Janeiro) register where appropriate.
After your Portuguese reply, on a new line emit exactly:

<<<META>>>{"correction": "...", "vocab": [{"pt": "...", "en": "..."}], "scenario_complete": false}

- correction: a short English tip on what the user could say better (empty string if nothing to correct).
- vocab: up to 3 new words/phrases from your reply worth saving.
- scenario_complete: true when the scenario has reached a natural end (after 5–8 turns).
```

**Response:** Stream plain text. The frontend splits on `<<<META>>>` — everything before is spoken via browser TTS, everything after is parsed as JSON for the correction tip and vocab pills.

Use prompt caching on the system prompt block:
```python
anthropic.messages.stream(
    model="claude-sonnet-4-6",
    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
    messages=history + [{"role": "user", "content": message}],
    max_tokens=300,
)
```

---

### POST /api/check-translation

AI-grades a free-text English translation (used by the Tests screen).

**Request:**
```json
{
  "original_pt":       "Quero um suco de laranja, por favor.",
  "user_translation_en": "I want a orange juice please"
}
```

**Behaviour:** Single short Claude call (no streaming). Ask Claude: "Is the meaning of this English translation correct for the Portuguese original? Reply with JSON only: {\"correct\": true/false, \"feedback\": \"one sentence\"}"

**Response:**
```json
{ "correct": true, "feedback": "Good — minor article error ('an orange juice') but meaning is correct." }
```

---

### GET /api/state

Returns saved user state. Used by the frontend on startup to hydrate across devices/sessions.

- Read from `state/user.json` (create the file and directory if missing).
- Return `{}` if file doesn't exist yet.

**Response:**
```json
{ "user": { "name": "Zac", "streak": 7, "xp": 240, "hearts": 4, "words_learned": 24 } }
```

---

### POST /api/state

Saves user state sent by the frontend (called after every significant action).

**Request:**
```json
{ "user": { "name": "Zac", "streak": 7, "xp": 255, "hearts": 4, "words_learned": 25 } }
```

- Write to `state/user.json`. Create `state/` directory if needed.
- Return `{ "ok": true }`.

> **Note for Railway:** The default Railway filesystem is ephemeral — `state/user.json` will reset on redeploy. For production persistence, swap the file read/write for a Supabase call or a Railway Postgres instance. The interface is identical; only the storage layer changes.

---

### POST /api/config

Stores the Anthropic API key sent from the Settings screen so it can be used for subsequent tutor calls.

**Request:**
```json
{ "api_key": "sk-ant-api03-..." }
```

- Store in `flask.session['api_key']` (requires `app.secret_key`).
- Return `{ "ok": true }`.

The key priority in all routes: `X-API-Key` header → `session['api_key']` → `ANTHROPIC_API_KEY` env var.

---

## data/vocab.json

Seed vocab for Week 1 — Food & Groceries. 40 words minimum. Each entry:

```json
{
  "id":         "cafezinho",
  "pt":         "cafezinho",
  "en":         "little coffee",
  "phonetic":   "[ka-fei-'zi-ɲu]",
  "category":   "food",
  "example_pt": "Vou tomar um cafezinho agora.",
  "example_en": "I'm going to have a little coffee now.",
  "due":        "2026-05-06",
  "interval":   4,
  "times_seen": 0
}
```

Organise by topic: `food`, `drinks`, `restaurant`, `market`. The frontend already has 15 of these as JS constants — use those as the base and expand to 40.

---

## Procfile

```
web: gunicorn --timeout 300 app:app
```

---

## requirements.txt

```
flask
anthropic
gunicorn
```

---

## API key handling (summary)

1. Frontend Settings screen → user enters key → stored in `localStorage` as `fr_v1_apikey`
2. Every fetch from the frontend sends `X-API-Key: <key>` header
3. Backend reads it: `key = request.headers.get('X-API-Key') or session.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')`
4. `/api/config` POST also saves the key to `session['api_key']` for tab-refresh survival

---

## Frontend stubs to wire up

Search `index.html` for `TODO` — three spots:

| Location | What to wire |
|---|---|
| `toggleMic()` | `SpeechRecognition({ lang: 'pt-BR' })` → on final transcript, POST `/api/tutor` → split stream on `<<<META>>>` → append bubble + populate dica + vocab pills |
| `checkTranslate()` | POST `/api/check-translation` instead of always returning `'correct'` |
| Speaking tutor card — 🔊 Ouvir button | `speechSynthesis.speak(new SpeechSynthesisUtterance(tutorPt))` with `lang: 'pt-BR'` |

---

## Environment variables (Railway)

| Var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Fallback if user hasn't set a key via the UI |
| `SECRET_KEY` | Flask session signing — set to a random string |
| `PORT` | Set automatically by Railway — `gunicorn` picks it up |
