import importlib.util
import os
from pathlib import Path

from fastapi.testclient import TestClient


def load_app():
    import sys
    import types
    service_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(service_root))

    # Provide dummy OpenAI client to satisfy run_process_calendar import-time usage
    class DummyChat:
        def __init__(self):
            self.completions = types.SimpleNamespace(create=lambda **kwargs: types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"ok": true}'))]))

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.chat = DummyChat()

    sys.modules["openai"] = types.SimpleNamespace(OpenAI=DummyOpenAI)
    os.environ.setdefault("OPENAI_API_KEY", "test-key")

    app_path = service_root / "app.py"
    spec = importlib.util.spec_from_file_location("calendar_agent_app", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_health():
    app_module = load_app()
    client = TestClient(app_module.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_planner_api_without_file(monkeypatch):
    app_module = load_app()
    client = TestClient(app_module.app)

    # Stub planner functions to avoid external services/DB
    monkeypatch.setattr(app_module, "fetch_user_profile", lambda user_id: {"id": user_id, "full_name": "Test"})
    monkeypatch.setattr(
        app_module, "generate_fitness_plan", lambda user_profile, calendar_payload: {"plan": "stubbed"}
    )
    monkeypatch.setattr(app_module, "save_plan_record", lambda user_id, plan: {"id": 1})

    resp = client.post(
        "/planner",
        data={"user_id": 1, "save_to_db": "false"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["id"] == 1
    assert body["fitness_plan"]["plan"] == "stubbed"
