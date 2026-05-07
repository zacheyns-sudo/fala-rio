import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = "/Users/zacheyns/fala-rio"


class FakeTextStream:
    def __init__(self, chunks):
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @property
    def text_stream(self):
        return iter(self.chunks)


class FakeMessages:
    def __init__(self, text=""):
        self.text = text
        self.stream_calls = []
        self.create_calls = []

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return FakeTextStream(["Oi! Tudo bem?\n", '<<<META>>>{"correction":"","vocab":[],"scenario_complete":false}'])

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        text = self.text

        class Response:
            content = [type("Block", (), {"text": text})()]

        return Response()


CREATED = []


class FakeAnthropic:
    def __init__(self, api_key):
        self.api_key = api_key
        self.messages = FakeMessages('{"correct": true, "feedback": "Meaning is correct."}')
        CREATED.append(self)


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["FALA_RIO_STATE_PATH"] = os.path.join(self.tmp.name, "state", "user.json")
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        if "app" in sys.modules:
            del sys.modules["app"]
        self.app_module = importlib.import_module("app")
        self.app_module.app.config.update(TESTING=True)
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_state_round_trip_creates_state_file(self):
        payload = {
            "user": {
                "name": "Zac",
                "readiness_goals": {"cafe": 72},
                "completed_scenarios": ["cafe"],
                "phrase_reviews": {"bora": {"confidence": "worked"}},
                "speaking_sessions": 3,
                "weak_tags": ["listening"],
            }
        }

        post_response = self.client.post("/api/state", json=payload)
        get_response = self.client.get("/api/state")

        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(post_response.get_json(), {"ok": True})
        self.assertEqual(get_response.get_json(), payload)

    def test_state_returns_empty_object_when_missing(self):
        response = self.client.get("/api/state")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {})

    def test_config_stores_api_key_in_session(self):
        response = self.client.post("/api/config", json={"api_key": "sk-ant-api03-test"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})
        with self.client.session_transaction() as session:
            self.assertEqual(session["api_key"], "sk-ant-api03-test")

    def test_translation_uses_header_key_before_environment(self):
        CREATED.clear()
        os.environ["ANTHROPIC_API_KEY"] = "env-key"
        with mock.patch.object(self.app_module.anthropic, "Anthropic", FakeAnthropic):
            response = self.client.post(
                "/api/check-translation",
                json={
                    "original_pt": "Quero um suco de laranja, por favor.",
                    "user_translation_en": "I want an orange juice please",
                },
                headers={"X-API-Key": "header-key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"correct": True, "feedback": "Meaning is correct."})
        self.assertEqual(CREATED[-1].api_key, "header-key")
        call = CREATED[-1].messages.create_calls[-1]
        self.assertEqual(call["model"], "claude-sonnet-4-6")
        self.assertEqual(call["max_tokens"], 120)

    def test_translation_returns_error_without_api_key(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)

        response = self.client.post(
            "/api/check-translation",
            json={"original_pt": "Olá", "user_translation_en": "Hello"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Anthropic API key is required.")

    def test_tutor_streams_text_and_uses_cached_system_prompt(self):
        CREATED.clear()
        with mock.patch.object(self.app_module.anthropic, "Anthropic", FakeAnthropic):
            response = self.client.post(
                "/api/tutor",
                json={
                    "history": [{"role": "user", "content": "Eu quero um café"}],
                    "message": "Quanto é?",
                    "scenario": "cafe",
                    "turn": 3,
                },
                headers={"X-API-Key": "stream-key"},
            )

        body = response.get_data(as_text=True)
        call = CREATED[-1].messages.stream_calls[-1]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Oi! Tudo bem?", body)
        self.assertIn("<<<META>>>", body)
        self.assertEqual(CREATED[-1].api_key, "stream-key")
        self.assertEqual(call["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(call["messages"][-1], {"role": "user", "content": "Quanto é?"})

    def test_tutor_prompt_requests_phrase_deck_metadata(self):
        prompt = self.app_module.tutor_system_prompt("cafe")

        self.assertIn("phrase deck", prompt)
        self.assertIn('"type"', prompt)
        self.assertIn('"register"', prompt)
        self.assertIn('"usage_note"', prompt)

    def test_frontend_uses_v2_readiness_model_instead_of_gamification(self):
        html = os.path.join(PROJECT_ROOT, "index.html")
        with open(html, encoding="utf-8") as source:
            frontend = source.read()

        self.assertIn("Rio Readiness", frontend)
        self.assertIn("phraseDeck", frontend)
        self.assertIn("readiness_goals", frontend)
        self.assertNotIn("XP", frontend)
        self.assertNotIn("streak", frontend.lower())
        self.assertNotIn("hearts", frontend.lower())

    def test_translation_handles_malformed_model_json(self):
        class BadAnthropic(FakeAnthropic):
            def __init__(self, api_key):
                self.api_key = api_key
                self.messages = FakeMessages("not json")

        with mock.patch.object(self.app_module.anthropic, "Anthropic", BadAnthropic):
            response = self.client.post(
                "/api/check-translation",
                json={"original_pt": "Olá", "user_translation_en": "Hello"},
                headers={"X-API-Key": "key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "correct": False,
                "feedback": "I could not grade that answer. Please try again.",
            },
        )


if __name__ == "__main__":
    unittest.main()
