import importlib.util
from pathlib import Path


def load_app():
    import sys
    import types

    sys.modules["db"] = types.SimpleNamespace(engine=None)
    sys.modules["etl"] = types.SimpleNamespace(run_etl=lambda: "ok")

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("core_etl_app_pw", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_password_hash_and_verify():
    app_module = load_app()
    hashed = app_module.get_password_hash("secret-pass")
    assert app_module.verify_password("secret-pass", hashed)
    assert not app_module.verify_password("wrong", hashed)
