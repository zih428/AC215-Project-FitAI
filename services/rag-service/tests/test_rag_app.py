import importlib.util
import sys
import types
from pathlib import Path


def load_rag_app():
    # Stub rag_core to avoid external dependencies
    stub = types.ModuleType("rag_core")
    stub.api_process_gcs_to_chromadb = lambda bucket, folder, method: {"status": "ok", "bucket": bucket, "method": method}
    stub.api_query_vector_db = lambda query, method, n_results: {
        "status": "ok",
        "query": query,
        "method": method,
        "n_results": n_results,
    }
    stub.api_chat_with_llm = lambda query, method, n_results, user_profile=None: {"status": "ok", "response": "stub"}
    stub.api_list_collections = lambda: {"status": "ok", "collections": []}
    sys.modules["rag_core"] = stub

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("rag_service_app", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_request_models_have_defaults():
    app_module = load_rag_app()

    gcs_req = app_module.GCSProcessRequest(bucket_name="demo")
    assert gcs_req.method == "char-split"

    chat_req = app_module.ChatRequest(query="hello")
    assert chat_req.n_results == 10
    assert chat_req.user_profile is None


def test_handlers_return_stubbed_values():
    app_module = load_rag_app()
    gcs_resp = app_module.process_gcs_to_chromadb(app_module.GCSProcessRequest(bucket_name="demo"))
    assert gcs_resp["status"] == "ok"

    query_resp = app_module.query_vector_db(app_module.QueryRequest(query="q"))
    assert query_resp["status"] == "ok"

    chat_resp = app_module.chat_with_llm(app_module.ChatRequest(query="q"))
    assert chat_resp["response"] == "stub"

    collections = app_module.list_collections()
    assert collections["collections"] == []
