# Model Training and Fine-Tuning Summary

## Model Design Choices
- Base: `gemini-2.0-flash-001` fine-tuned via Vertex AI Supervised Fine-Tuning (SFT) to balance latency and cost for real-time RAG.
- Goals: embed domain expertise (exercise physiology, recovery, nutrition) and improve grounding with retrieved literature.
- Deployment fit: tuned model is exposed at a Vertex endpoint and consumed directly by `services/rag-service` (`GENERATIVE_MODEL` in `rag_core.py`), so FastAPI and embedding logic remain unchanged.

## Datasets (versioned)
- Source corpus: scientific fitness literature already tracked via DVC at `fitai_data_bucket.dvc` (GCS bucket).
- Supervised datasets (instructional Q&A):
  - `gs://fitai-data-bucket/sft/sft_v1.jsonl` (`sft/sft_v1.jsonl.dvc`, md5 `cb80c4ead8752957198aaf7c9d3166ec`, 11,046 bytes)
  - `gs://fitai-data-bucket/sft/sft_v2.jsonl` (`sft/sft_v2.jsonl.dvc`, md5 `0a32811a4834d14250c1e372fd4c6387`, 101,592 bytes)
- Each example: system instruction + user profile + question → literature-grounded answer; stored as Vertex SFT JSONL format.

## Training Assets
- Config: `sft/sft_config.yaml` (project/location, base model, dataset prefix, observed training metadata and output placeholders).
- Launch script: `sft/train_sft.py` loads YAML, initializes Vertex, submits SFT job, polls to completion, and writes tuned model/endpoint IDs back into the YAML.
- Monitoring: `sft/get_tuning_job.py` fetches job state/details by ID; useful for post-mortem or audit.
- Dataset upload helper: `sft/upload_to_gcs.py` (local JSONL → GCS under `sft/`).
- Smoke test: `sft/test_sft_model.py` queries the deployed endpoint for a sample recovery-plan prompt.

## Training Process
- Platform: Vertex AI SFT (managed training loop, tokenization, checkpointing, and deployment).
- Hyperparameters: Vertex defaults (epochs, LR schedule, etc.); observed values captured in `training_metadata` (40 epochs, 6 default checkpoints, learning_rate_multiplier 2).
- Execution steps:
  1) Prepare/validate JSONL dataset, upload to `gs://fitai-data-bucket/sft/`.
  2) Ensure `dataset.train_dataset` in `sft_config.yaml` points to the desired version (`sft_v1` or `sft_v2`).
  3) `python sft/train_sft.py` (requires authenticated gcloud/service account).
  4) On completion, YAML is updated with `tuned_model`, `endpoint`, and `experiment`.
  5) Update `GENERATIVE_MODEL` in `services/rag-service/rag_core.py` if a new endpoint is produced.

## Results and Evaluation
- Tuning outcome (v1):
  - Status: succeeded; 40 epochs; 6 checkpoints.
  - Final training accuracy: ~99.7%; loss: ~0.014.
  - Endpoint: `projects/767605785387/locations/us-central1/endpoints/5283592076603162624`.
- Qualitative evaluation:
  - Better synthesis of retrieved literature, more structured and evidence-based answers, reduced hallucinations.
  - Example prompt (“What should I do after heavy squats to minimize soreness?”): tuned model recommends active recovery/compression and cautions against immediate cryotherapy, tied to literature context.
- RAG impact:
  - Drop-in replacement improves grounding without changing API contracts.
  - Fallback to the base Gemini Flash remains possible by swapping the endpoint/model ID.

## Reproducing Experiments
- Fetch datasets: `dvc pull sft/sft_v1.jsonl.dvc` (or `sft_v2`) with GCS credentials.
- Configure: set `project`, `location`, and dataset version in `sft_config.yaml`.
- Train: `python sft/train_sft.py` (ensure Vertex quota and service account permissions).
- Validate: run `python sft/test_sft_model.py` to sanity-check the deployed endpoint; optionally compare against the base model using the same prompts.
