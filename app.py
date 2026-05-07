import json
import os
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, Response, jsonify, request, send_from_directory, session, stream_with_context

try:
    import anthropic
except ImportError:
    anthropic = SimpleNamespace(Anthropic=None)


BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = Path(os.environ.get("FALA_RIO_STATE_PATH", BASE_DIR / "state" / "user.json"))
MODEL = "claude-sonnet-4-6"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


def resolve_api_key():
    return (
        request.headers.get("X-API-Key")
        or session.get("api_key")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def anthropic_client(api_key):
    if not anthropic.Anthropic:
        raise RuntimeError("The anthropic package is not installed.")
    return anthropic.Anthropic(api_key=api_key)


def tutor_system_prompt(scenario):
    return f"""You are a Brazilian Portuguese conversation tutor running a scenario called "{scenario}".
Reply ONLY in Brazilian Portuguese - 1-2 short sentences, conversational and natural.
Use Carioca (Rio de Janeiro) register where appropriate.
This app saves useful language into a unified phrase deck, so prefer practical words, short phrases, and Carioca slang that a Rio exchange student can reuse.
After your Portuguese reply, on a new line emit exactly:

<<<META>>>{{"correction": "...", "vocab": [{{"pt": "...", "en": "...", "type": "word|phrase|slang", "register": "neutral|casual|slang", "usage_note": "..."}}], "scenario_complete": false}}

- correction: a short English tip on what the user could say better (empty string if nothing to correct).
- vocab: up to 3 new phrase deck items from your reply worth saving. Include the type, register, and a short usage_note that explains when to use it.
- scenario_complete: true when the scenario has reached a natural end (after 5-8 turns)."""


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(BASE_DIR / "assets", filename)


@app.post("/api/tutor")
def tutor():
    api_key = resolve_api_key()
    if not api_key:
        return Response("Anthropic API key is required.", status=401, mimetype="text/plain")

    payload = request.get_json(silent=True) or {}
    history = payload.get("history") or []
    message = payload.get("message") or ""
    scenario = payload.get("scenario") or "cafe"

    messages = history + [{"role": "user", "content": message}]
    system_prompt = tutor_system_prompt(scenario)

    def generate():
        try:
            client = anthropic_client(api_key)
            with client.messages.stream(
                model=MODEL,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                max_tokens=300,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as exc:
            yield f"\n<<<META>>>{json.dumps({'correction': str(exc), 'vocab': [], 'scenario_complete': False})}"

    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.post("/api/check-translation")
def check_translation():
    api_key = resolve_api_key()
    if not api_key:
        return jsonify({"error": "Anthropic API key is required."}), 401

    payload = request.get_json(silent=True) or {}
    original_pt = payload.get("original_pt") or ""
    user_translation = payload.get("user_translation_en") or ""
    prompt = (
        "Is the meaning of this English translation correct for the Portuguese original? "
        'Reply with JSON only: {"correct": true/false, "feedback": "one sentence"}\n\n'
        f"Portuguese original: {original_pt}\n"
        f"English translation: {user_translation}"
    )

    try:
        client = anthropic_client(api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        graded = json.loads(raw)
        return jsonify(
            {
                "correct": bool(graded.get("correct")),
                "feedback": graded.get("feedback") or "",
            }
        )
    except json.JSONDecodeError:
        return jsonify(
            {
                "correct": False,
                "feedback": "I could not grade that answer. Please try again.",
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/api/state")
def get_state():
    if not STATE_PATH.exists():
        return jsonify({})
    try:
        return jsonify(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return jsonify({})


@app.post("/api/state")
def save_state():
    payload = request.get_json(silent=True) or {}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True})


@app.post("/api/config")
def config():
    payload = request.get_json(silent=True) or {}
    api_key = (payload.get("api_key") or "").strip()
    if api_key:
        session["api_key"] = api_key
    else:
        session.pop("api_key", None)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
