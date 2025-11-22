# Data Versioning Workflow

## Approach
- Method: Data Version Control (DVC) with a GCS remote (`gs://fitai-data-bucket`). We track large artifacts as pointers instead of duplicating them locally, keeping Git lightweight while preserving lineage.
- Justification: Literature and SFT datasets are large, semi-static, and shared across the team. DVC’s remote-only tracking lets any Git commit map to an exact dataset snapshot without storing data in the repo.
- Scope: Literature corpus (raw/processed text, PDFs) and supervised fine-tuning JSONL datasets.

## Current Tracked Artifacts
- Literature bucket pointer: `fitai_data_bucket.dvc` (remote-only, frozen import of the entire bucket).
- SFT training sets: `sft/sft_v1.jsonl.dvc`, `sft/sft_v2.jsonl.dvc` (stored in GCS under `sft/`).
- Remote config: `.dvc/config` points to `gs://fitai-data-bucket` (`remote "literature-remote"`).

## Version History (snapshots in Git)
- `fitai_data_bucket.dvc` → md5 `29f86f5aa17aeefe316e4dd424e3765a`, size 50,950,203 bytes, 41 files (GCS bucket state).
- `sft/sft_v1.jsonl.dvc` → md5 `cb80c4ead8752957198aaf7c9d3166ec`, size 11,046 bytes (first SFT dataset).
- `sft/sft_v2.jsonl.dvc` → md5 `0a32811a4834d14250c1e372fd4c6387`, size 101,592 bytes (expanded SFT dataset).

## Workflows
- Initialize (one time)
  - `dvc pull fitai_data_bucket.dvc` to materialize a local copy if needed (requires GCS credentials with read access).
  - Ensure DVC uses the configured remote: `dvc remote list`.
- Refresh literature snapshot (update pointer only)
  - `dvc update fitai_data_bucket.dvc`
  - `git add fitai_data_bucket.dvc && git commit -m "Update literature snapshot"`
- Retrieve datasets
  - Literature: `dvc pull fitai_data_bucket.dvc`
  - SFT data: `dvc pull sft/sft_v1.jsonl.dvc` or `dvc pull sft/sft_v2.jsonl.dvc`
- Publish new SFT data version
  - Place new JSONL under `sft/` (or import-url from GCS), run `dvc add sft/sft_vX.jsonl`, then `dvc push sft/sft_vX.jsonl.dvc`, commit the `.dvc` file.
- Credentials
  - Requires GCS service account with access to `fitai-data-bucket`. Set `GOOGLE_APPLICATION_CREDENTIALS` or configure gcloud default credentials prior to DVC commands.

## LLM-Generated Artifacts
- Current workflows use inference-only LLM calls for RAG and do not persist prompt/output datasets. If future pipelines generate synthetic data, add them to DVC with the same remote and record prompts/outputs alongside the `.dvc` pointer.
