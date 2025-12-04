# Model Training and Fine-Tuning Summary

## Model Design Choices
	•	Base model: gemini-2.5-flash, fine-tuned via Vertex AI Supervised Fine-Tuning (SFT) to balance latency, cost, and real-time RAG performance
	•	Goal: Embed domain expertise in exercise physiology, recovery, and nutrition while improving grounding with retrieved scientific literature
	•	Deployment: The tuned model is exposed as a Vertex Endpoint and consumed directly by services/rag-service via GENERATIVE_MODEL in rag_core.py, leaving FastAPI and retrieval logic unchanged
	•	Automation split:
	•	SFT is manually triggered for intentional and low-frequency model upgrades
	•	RAG retraining is fully automated and triggered by new literature uploads

## Datasets (Versioned)
	•	Source corpus for RAG
    Scientific fitness literature tracked via DVC at fitai_data_bucket.dvc
	•	Physical storage: gs://fitai-data-bucket/processed-literature/
	  This corpus is automatically re-embedded and indexed on every new upload
	•	Supervised datasets for SFT (instructional Q&A)
	  gs://fitai-data-bucket/sft/sft_v1.jsonl
    (sft/sft_v1.jsonl.dvc, md5 cb80c4ead8752957198aaf7c9d3166ec, 11,046 bytes)
	  gs://fitai-data-bucket/sft/sft_v2.jsonl
    (sft/sft_v2.jsonl.dvc, md5 0a32811a4834d14250c1e372fd4c6387, 101,592 bytes)
	•	Data format
	  Each example contains: system instruction + user profile + user question → literature-grounded answer
	  Stored in Vertex SFT JSONL format

## Training Assets
	•	Config: sft/sft_config.yaml
    Controls project/location, base model, dataset prefix, training metadata, and tuned model + endpoint outputs
	•	Launcher: sft/train_sft.py
    Loads YAML, initializes Vertex AI, submits the SFT job, polls to completion, and writes tuned model and endpoint IDs back into the YAML
	•	Monitoring: sft/get_tuning_job.py
    Fetches job state and metadata for auditing and debugging
	•	Dataset upload helper: sft/upload_to_gcs.py
    Uploads local JSONL datasets to gs://fitai-data-bucket/sft/
	•	Smoke test: sft/test_sft_model.py
    Queries the deployed endpoint with recovery and training prompts

## Training Process
	•	Platform: Vertex AI SFT (managed fine-tuning, tokenization, checkpointing, and deployment)
	•	Hyperparameters recorded in training_metadata:
	  •	40 epochs
	  •	6 checkpoints
	  •	learning_rate_multiplier = 2
	•	Execution flow:
    •	Prepare and validate JSONL dataset locally
    •	Upload to gs://fitai-data-bucket/sft/
    •	Update dataset.train_dataset in sft_config.yaml (sft_v1 or sft_v2)
    •	Run python sft/train_sft.py
    •	YAML is updated with tuned_model, endpoint, and experiment
    •	Update GENERATIVE_MODEL in services/rag-service/rag_core.py when adopting a new endpoint

## Automated RAG Retraining (Cloud Run Trigger)
	•	Unlike SFT, the RAG knowledge base is retrained fully automatically
	•	Architecture:
    GCS Upload → Eventarc Trigger → Cloud Run (fitai-gcs-trigger)
    → POST /process-gcs → Chunking → Embedding → ChromaDB
	•	Trigger source: gs://fitai-data-bucket/processed-literature/
	•	Processor
    •	Cloud Run service: fitai-gcs-trigger
    •	Automatically calls /process-gcs in the RAG service
	•	Storage
    •	Embedded vectors are inserted into ChromaDB
    •	New documents become immediately available for retrieval
	•	Capabilities
    •	Zero-downtime literature ingestion
    •	Continuous RAG updates without retraining the base model
    •	Fully automated production data-to-vector pipeline

## Results and Evaluation
	•	Tuning outcomes
    •	v1 endpoint:
  projects/767605785387/locations/us-central1/endpoints/5283592076603162624
    •	v2 endpoint (current production):
  projects/767605785387/locations/us-central1/endpoints/7589646192049389568
	•	Status: succeeded; 40 epochs; 6 checkpoints
	•	Final training accuracy: ~99.7%
	•	Final loss: ~0.014
	•	Qualitative improvements
    •	Better synthesis of retrieved literature
    •	More structured and evidence-based responses
    •	Reduced hallucinations
    •	Robust handling of greetings, off-topic queries, and insufficient-information cases
	•	Example
	  •	For “What should I do after heavy squats to minimize soreness?”, the tuned model recommends active recovery and compression and cautions against early cryotherapy, aligned with literature
	•	RAG impact
    •	Drop-in replacement improves grounding without changing API contracts
    •	Fallback to base Gemini remains possible by swapping the endpoint

## Validation and Deployment Gate
	•	Validation dataset: sft/sft_validation.jsonl
	•	Validation workflow：
    •	Load validation samples
    •	Send each prompt to the live Vertex endpoint
    •	Compute accuracy automatically
	•	Deployment rule
    •	accuracy ≥ 0.65 → deployment allowed
    •	accuracy < 0.65 → deployment blocked
    •	This enforces an automated quality gate before production adoption

## Reproducing Experiments
	•	Fetch datasets: dvc pull sft/sft_v1.jsonl.dvc
	•	Configure
	•	Set project, location, and dataset version in sft_config.yaml
	•	Train: python sft/train_sft.py
	•	Validate: python sft/test_sft_model.py
	•	Automated RAG retraining
	•	Upload any new .txt file to gs://fitai-data-bucket/processed-literature/
	•	The system automatically re-chunks, re-embeds, and updates ChromaDB
