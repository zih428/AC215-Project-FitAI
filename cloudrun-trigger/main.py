from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 你的 RAG 服务地址（K8S 暴露的端口）
RAG_API_URL = "http://34.63.130.184:8002/process-gcs"

@app.route("/", methods=["POST"])
def gcs_trigger():
    data = request.get_json()
    print("✅ GCS Event Received:", data)

    payload = {
        "bucket_name": "fitai-data-bucket",
        "folder_path": "processed-literature",
        "method": "semantic-split"
    }

    r = requests.post(RAG_API_URL, json=payload)
    return jsonify({
        "status": "triggered",
        "rag_response": r.text
    })

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)