import time
import vertexai
from vertexai.tuning import sft

vertexai.init(
    project="rich-access-471117-r0",
    location="us-central1"
)

print("🚀 Starting SFT tuning job...")

hyper_parameters = {
    "epoch_count": 5,                # ↓ from 40
    "learning_rate_multiplier": 3,   # ↓ from 5
    "adapter_size": "ADAPTER_SIZE_ONE"  # ↓ from FOUR
}

sft_tuning_job = sft.train(
    source_model="gemini-2.0-flash-001",
    train_dataset="gs://fitai-data-bucket/sft/sft_v1.jsonl",
    hyper_parameters=hyper_parameters
)

print("✅ Tuning job submitted. Waiting for completion...")
print("   Job name:", sft_tuning_job.resource_name)

while not sft_tuning_job.has_ended:
    print("⏳ Still running... (checking again in 60s)")
    time.sleep(60)
    sft_tuning_job.refresh()

print("🎉 FINISHED!")
print("TUNED MODEL NAME:", sft_tuning_job.tuned_model_name)
print("ENDPOINT:", sft_tuning_job.tuned_model_endpoint_name)
print("EXPERIMENT:", sft_tuning_job.experiment)