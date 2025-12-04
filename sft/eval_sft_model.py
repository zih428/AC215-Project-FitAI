import json
import os
import sys
import subprocess
import requests


VALIDATION_FILE = "sft/sft_validation.jsonl"

VERTEX_ENDPOINT = os.getenv(
    "VERTEX_ENDPOINT",
    "projects/767605785387/locations/us-central1/endpoints/7589646192049389568"
)

REGION = "us-central1"
ACCURACY_THRESHOLD = 0.65

def get_gcp_token():
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"]
        ).decode("utf-8").strip()
        return token
    except Exception:
        print("❌ Failed to get GCP access token. Make sure gcloud is installed and authenticated.")
        sys.exit(1)


def load_validation_data(path):
    if not os.path.exists(path):
        print(f"❌ Validation file not found: {path}")
        sys.exit(1)

    data = []
    with open(path, "r") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def predict(prompt, token):
    url = f"https://{REGION}-aiplatform.googleapis.com/v1/{VERTEX_ENDPOINT}:predict"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "instances": [
            {"content": prompt}
        ]
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    if resp.status_code != 200:
        print("❌ Vertex prediction failed:")
        print(resp.text)
        sys.exit(1)

    return resp.json()["predictions"][0]["content"]


def evaluate(samples):
    token = get_gcp_token()
    correct = 0

    for i, sample in enumerate(samples):
        user_input = sample["input"]
        target = sample["output"]

        pred = predict(user_input, token)

        print(f"\n[{i+1}] USER:", user_input)
        print("EXPECTED:", target)
        print("PREDICTED:", pred)

        if target.strip().lower() == pred.strip().lower():
            correct += 1

    acc = correct / len(samples)
    return acc


if __name__ == "__main__":
    print("\n🔍 Loading validation dataset...")
    samples = load_validation_data(VALIDATION_FILE)

    print(f"✅ Loaded {len(samples)} validation samples")
    print("🚀 Running validation on Vertex Endpoint:")
    print("📡 Using endpoint:", VERTEX_ENDPOINT)

    acc = evaluate(samples)

    print("\n==============================")
    print(f"✅ Validation Accuracy: {acc:.4f}")
    print("==============================")

    if acc >= ACCURACY_THRESHOLD:
        print("✅ Model PASSED validation. Deployment allowed.")
        sys.exit(0)
    else:
        print("❌ Model FAILED validation. Deployment BLOCKED.")
        sys.exit(1)