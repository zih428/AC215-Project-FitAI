import importlib.util
import sys
import types
from pathlib import Path


def load_core_app():
    # Stub ETL to avoid external storage dependencies
    sys.modules["etl"] = types.SimpleNamespace(run_etl=lambda: "ok")
    # Stub DB engine so import db works
    sys.modules["db"] = types.SimpleNamespace(engine=None)

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("core_etl_app", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_health_route():
    app_module = load_core_app()
    resp = app_module.health_check()
    assert resp["status"] == "ok"
    assert resp["service"] == "core-etl-api"


def test_token_generation_round_trip():
    app_module = load_core_app()
    token = app_module.create_access_token({"sub": 123})
    decoded = app_module.jwt.decode(token, app_module.JWT_SECRET, algorithms=[app_module.JWT_ALGORITHM])
    assert decoded["sub"] == "123"
