import time
import yaml
import vertexai
from vertexai.tuning import sft

CONFIG_PATH = "sft/sft_config.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, sort_keys=False)


def main():
    cfg = load_config()

    project = cfg["project"]
    location = cfg["location"]
    base_model = cfg["model"]["base_model"]
    dataset_name = cfg["dataset"]["train_dataset"]
    gcs_prefix = cfg["dataset"]["gcs_path_prefix"]
    gcs_dataset = f"{gcs_prefix}{dataset_name}.jsonl"

    vertexai.init(project=project, location=location)

    job = sft.train(
        source_model=base_model,
        train_dataset=gcs_dataset
    )

    while not job.has_ended:
        time.sleep(60)
        job.refresh()

    cfg["output"]["tuned_model"] = job.tuned_model_name
    cfg["output"]["endpoint"] = job.tuned_model_endpoint_name
    cfg["output"]["experiment"] = job.experiment

    save_config(cfg)


if __name__ == "__main__":
    main()