# sft/test_sft_model.py
import os
from vertexai.generative_models import GenerativeModel
import vertexai

PROJECT_ID = "rich-access-471117-r0"
LOCATION = "us-central1"

ENDPOINT = "projects/767605785387/locations/us-central1/endpoints/5283592076603162624"

def main():
    print("🚀 Loading tuned model from endpoint...")

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    tuned_model = GenerativeModel(ENDPOINT)

    prompt = "Give me a short lower-body recovery plan after heavy squats."

    response = tuned_model.generate_content(prompt)

    print("\n=== SFT MODEL RESPONSE ===")
    print(response.text)

if __name__ == "__main__":
    main()