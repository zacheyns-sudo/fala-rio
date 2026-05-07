# Fala Rio — Design Spec
*Date: 2026-05-04*

## Overview

A Brazilian Portuguese learning app built for a PUC-Rio exchange student. Combines voice-to-voice AI conversation practice with spaced repetition vocabulary, written tests, and progress tracking. Built as a single-file Flask + HTML app (same pattern as Study Buddy) — no build step, no framework, deploys to Railway.

Target user: an English speaker living in Rio for a semester who needs practical, conversational Brazilian Portuguese fast.

---

## Architecture

**Same two-file pattern as Study Buddy:**

- `app.py` — Flask backend. Handles AI tutor calls and vocab data serving.
- `index.html` — Single-file SPA (HTML + embedded CSS + vanilla JS). No build step. SRS scheduling logic lives here.

**State:** All user state stored in `localStorage` under `fr_v1_*` keys, namespaced for a future Supabase migration.

**Model:** `claude-sonnet-4-6` for the AI tutor via Anthropic API.

**Deployment:** Railway via `Procfile` (`gunicorn --timeout 300 app:app`).

---

## Screens & Navigation

4-tab bottom nav: **Home · Vocab · Tests · Progress**

Speaking Practice is accessed from the Home screen (not a nav tab — it's the primary daily action).

### 1. Home / Dashboard

**Layout: Progress-first (Option B)**

- Large ocean-blue gradient hero (`#075985 → #0284c7 → #0ea5e9`) with motivational greeting ("Bom dia! 👋"), streak badge, current topic label
- Speaking Practice CTA embedded in the hero as a white card with gradient "Start →" button
- Below hero: two mini-stat cards with progress bars — "Vocab Due" (amber) and "Accuracy" (green)
- Vocab reminder row: shows count of cards due with preview of first few words
- 4-tab bottom nav

### 2. Speaking Practice

**Layout: Hybrid (frosted bubbles on gradient + compact white tutor card)**

**Reply state:**
- Full ocean-blue gradient background throughout
- Chat history as frosted glass bubbles (tutor left, user right)
- Compact white card floating at bottom: tutor's Portuguese reply + English translation, Replay / Slower buttons, yellow correction tip block, vocab pills with ＋ save button
- Idle waveform bars flanking a white mic button ("Tap to reply")

**Listening state:**
- Same gradient + chat bubbles
- White card dismissed; mic area expands to a frosted glass container with animated waveform bars and "🎙 Listening…" label
- Live transcript appears as a bordered bubble in the chat area as the user speaks

**Interaction flow:**
1. Tutor speaks (TTS via `speechSynthesis`, `lang: 'pt-BR'`) and reply card appears
2. User taps mic → listening state activates (Web Speech API `SpeechRecognition`, `lang: 'pt-BR'`)
3. Final transcript sent to `/api/tutor` → streams back next tutor turn
4. Repeat until scenario complete

**Scenario structure:** Each scenario is a short conversational task (e.g., "Order food at a café"). 5–9 turns. Tutor adapts difficulty to user responses.

### 3. Vocab Review

**Layout: Revealed with Context (Option B)**

- One card at a time
- Word + translation displayed together (no flip required)
- Usage example sentence below in a blue-bordered block
- Two-button rating: **"Not quite"** (red, see again in 1 day) / **"Got it!"** (green, next interval)
- SRS intervals: Again=1d, Hard=2d, Good=4d, Easy=7d — simplified to Again/Got it maps to 1d/4d
- Progress bar at top showing cards remaining in session
- Category chip (e.g., "☕ Food") on each card

### 4. Tests

**Format: Mixed, configurable in Settings**

Three question types served in a single session, mix ratio configurable:

- **Multiple Choice** — 4 options, tap to select, instant green/red feedback
- **Fill in the Blank** — sentence with a gap, word bank to tap from
- **Translation / Free Type** — full sentence to translate, typed answer, AI checks meaning (not word-for-word)

Settings toggle: Mixed (default) / Multiple Choice only / Fill in the Blank only / Translation only.

Timer shown in header (display only, no time limit in v1).

### 5. Progress

**Layout: Journey & Milestones (Option B)**

- Level + XP bar: Beginner → Intermediate → Advanced (500 XP, 1500 XP gates). XP earned: +10 per speaking turn, +5 per vocab card reviewed, +15 per test question correct, +20 per scenario completed
- Milestone achievements: first conversation, 5-day streak, 10 speaking sessions, 50 words learned, etc.
- Quick stats row: Words learned · Streak · Accuracy
- Topic completion: locked topics revealed as user progresses

---

## Data Model

### Vocab Entry (localStorage: `fr_v1_vocab`)
```json
{
  "id": "cafezinho",
  "pt": "cafezinho",
  "en": "little coffee",
  "category": "food",
  "example_pt": "Vou tomar um cafezinho agora.",
  "example_en": "I'm going to have a little coffee now.",
  "due": "2026-05-05",
  "interval": 4,
  "times_seen": 3
}
```

### User State (localStorage: `fr_v1_state`)
```json
{
  "streak": 5,
  "last_active": "2026-05-04",
  "xp": 240,
  "words_learned": 24,
  "accuracy_history": [0.8, 0.85, 0.75, 0.9, 0.83],
  "milestones": ["first_convo", "streak_5"],
  "test_format": "mixed",
  "current_topic": "food"
}
```

### Conversation History (localStorage: `fr_v1_history`)
Array of `{role, content}` objects for the current speaking session. Cleared on new scenario.

---

## API Routes

### `POST /api/tutor`
Runs the voice-to-voice tutor turn. Streams back plain text.

**Request:**
```json
{
  "history": [...],
  "message": "Eu quero um café, por favor",
  "scenario": "ordering_food",
  "turn": 2
}
```

**Response:** Streamed plain text — the tutor's next Portuguese utterance. The system prompt instructs Claude to:
- Reply in Brazilian Portuguese only (no English in the reply itself)
- Keep turns short (1–2 sentences)
- Correct gently and naturally within the conversation
- After the reply, emit a JSON metadata block on its own line, delimited by `\n\n<<<META>>>`: `<<<META>>>{"correction": "...", "vocab": [...], "scenario_complete": false}`

Client splits the stream on `<<<META>>>` — everything before is the speakable Portuguese text, everything after is parsed as JSON for the correction tip and vocab pills.

### `GET /api/vocab`
Returns the Week N vocab list for a given topic. Seeded from `data/vocab.json` in the repo.

### `POST /api/check-translation`
Used by the Translation test type. Sends `{original_pt, user_translation_en}`, returns `{correct: bool, feedback: str}`.

---

## Vocab Data

Seeded vocab in `data/vocab.json`, organised by topic and week. Week 1 = Food & Ordering. 40 words per topic. Each word includes `pt`, `en`, `example_pt`, `example_en`, `category`.

Topics (unlock sequentially):
1. Food & Groceries
2. Transport & Directions
3. Beach & Outdoors
4. Shopping & Markets
5. Social & Nightlife
6. University & Admin

---

## Visual Design

**Palette:** Ocean blue — `#075985` (dark) · `#0284c7` (mid) · `#0ea5e9` (light) · `#38bdf8` (accent)  
**Accent:** Amber `#f59e0b` for streaks/urgency · Green `#10b981` for accuracy/success  
**Background:** `#f0f9ff` (light screens) · full gradient (speaking screen)  
**Font:** `Inter, system-ui, sans-serif`  
**Cards:** White, `border-radius: 14–18px`, `box-shadow: 0 2px 8px rgba(2,132,199,.1)`  
**Gradient:** `linear-gradient(160deg, #075985 0%, #0284c7 55%, #0ea5e9 100%)`

---

## Build Stages

### Stage 1 (this spec)
- Flask app scaffolding (`app.py` + `index.html`)
- Speaking Practice screen — full voice-to-voice flow (`/api/tutor`)
- Dashboard stub — hero, streak, speaking CTA
- Week 1 vocab data (`data/vocab.json` — Food & Groceries, 40 words)

### Stage 2
- Vocab Review screen — SRS flashcards with revealed+context layout
- SRS scheduling logic in JS (due dates, intervals)
- Dashboard vocab due count wired up

### Stage 3
- Tests screen — all three question types
- Settings screen — test format toggle (Mixed / MC only / Fill-in-blank only / Translation only), plus a "Reset progress" option
- `/api/check-translation` route

### Stage 4
- Progress screen — Journey & Milestones layout
- XP system, milestone triggers
- Topic unlock logic

### Stage 5
- Remaining vocab topics (2–6)
- Speaking scenarios expanded (5 per topic)
- Phrase bank (saved vocab pills from speaking screen)

### Stage 6
- Polish: animations, haptic feedback hints, onboarding flow
- Supabase migration prep (swap localStorage reads/writes to API calls)

---

## Key Constraints

- No build step — everything in two files, plain JS
- Web Speech API for STT/TTS — works in Chrome/Safari on iOS/macOS, not Firefox
- Prompt caching on `/api/tutor` system prompt (scenario context cached with `cache_control: ephemeral`)
- localStorage is the source of truth in Stage 1–5; keys namespaced `fr_v1_*` for clean migration
