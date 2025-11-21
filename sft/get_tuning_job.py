import vertexai
from vertexai.tuning import sft

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ID = "rich-access-471117-r0"
LOCATION = "us-central1"

TUNING_JOB_ID = "9001935944118435840"

def get_tuning_job_details():
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    job_resource_name = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/tuningJobs/{TUNING_JOB_ID}"
    )

    tuning_job = sft.SupervisedTuningJob(job_resource_name)

    print("🔍 Tuning Job Details:")
    print(tuning_job)
    print(f"\nresource name: {tuning_job.resource_name}")

    print("\n----- FIELDS -----")
    print("State:", tuning_job.state)

    try:
        print("Base model:", tuning_job.source_model)
    except:
        print("Base model: <field not exposed in SDK>")

    try:
        print("Dataset:", tuning_job.training_dataset_uri)
    except:
        print("Dataset: <field not exposed in SDK>")

    try:
        print("Created:", tuning_job.create_time)
    except:
        print("Created: <field missing>")

    try:
        print("Updated:", tuning_job.update_time)
    except:
        print("Updated: <field missing>")

    try:
        print("Model output:", tuning_job.tuned_model_name)
    except:
        print("Model output: <not available>")

    try:
        print("Endpoint:", tuning_job.tuned_model_endpoint_name)
    except:
        print("Endpoint: <not available>")

    print("\n----- FULL RAW JOB (FOR DEBUGGING) -----")
    print(tuning_job._gca_resource)


if __name__ == "__main__":
    get_tuning_job_details()