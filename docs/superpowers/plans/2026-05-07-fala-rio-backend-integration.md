# Fala Rio Backend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Flask backend from `CODEX.md` and connect the existing frontend TODOs so Fala Rio works end to end.

**Architecture:** A small Flask app owns Anthropic calls, local JSON state persistence, session API-key storage, and serving the existing `index.html`. The frontend remains a vanilla single-file SPA and calls the backend with `fetch`, streaming tutor text where needed.

**Tech Stack:** Flask, Anthropic Python SDK, Gunicorn, vanilla HTML/CSS/JavaScript, pytest for local backend tests.

---

### Task 1: Backend Tests

**Files:**
- Create: `tests/test_app.py`

- [ ] Create tests for state persistence, API key priority, config session storage, translation grading, tutor streaming, and missing-key errors.
- [ ] Run `python3 -m pytest tests/test_app.py -q`.
- [ ] Expected result before implementation: pytest cannot import `app` or route behavior is missing.

### Task 2: Flask Backend

**Files:**
- Create: `app.py`
- Create: `requirements.txt`
- Create: `Procfile`

- [ ] Implement Flask app routes: `/`, `/api/tutor`, `/api/check-translation`, `/api/state`, and `/api/config`.
- [ ] Implement API key lookup as `X-API-Key`, session key, then `ANTHROPIC_API_KEY`.
- [ ] Implement Anthropic streaming for tutor turns and guarded JSON parsing for translation grading.
- [ ] Run `python3 -m pytest tests/test_app.py -q`.
- [ ] Expected result after implementation: all backend tests pass.

### Task 3: Seed Vocabulary

**Files:**
- Create: `data/vocab.json`

- [ ] Add at least 40 Week 1 Food & Groceries vocab entries using the schema in `CODEX.md`.
- [ ] Run a JSON validation check with `python3 -m json.tool data/vocab.json`.
- [ ] Expected result: valid JSON with no parse errors.

### Task 4: Frontend Wiring

**Files:**
- Modify: `index.html`

- [ ] Replace speaking demo-only state with live speaking messages and tutor card state.
- [ ] Implement `SpeechRecognition` in `toggleMic()` using `pt-BR`.
- [ ] Stream `/api/tutor`, split on `<<<META>>>`, update tutor text, correction tip, vocab pills, and speak the Portuguese reply.
- [ ] Wire Replay and Slower buttons to `speechSynthesis`.
- [ ] Replace translation TODO with a `POST /api/check-translation` call and score from the response.
- [ ] Run text checks to confirm the three TODOs are gone and backend route names are present.

### Task 5: Verification

**Files:**
- Check: all changed files

- [ ] Run `python3 -m pytest tests/test_app.py -q`.
- [ ] Run `python3 -m json.tool data/vocab.json`.
- [ ] Run a Flask import check with `python3 - <<'PY'\nfrom app import app\nprint(app.name)\nPY`.
- [ ] Inspect `git diff -- fala-rio` from the repository root and confirm only the intended app files changed.
