# FitAI

FitAI delivers personalized fitness recommendations by combining user profiles with research-backed context retrieved through a RAG pipeline. The app is already live on GKE with autoscaling at http://34.71.139.146/login. Architecture diagrams live in [docs/solution-architecture.jpeg](docs/solution-architecture.jpeg) and [docs/technical-architecture.jpeg](docs/technical-architecture.jpeg), and service-level details are documented in the individual READMEs under [services/](services/) plus [infra/README.md](infra/README.md). UI previews are in [docs/UI_Screens.md](docs/UI_Screens.md).

## Prerequisites and setup instructions
- **Local:** Install Docker and Docker Compose; exposed ports: frontend 3000, core-etl-api 8001, rag-service 8002, ocr-engine 8003, calendar-agent 8004, Chroma 8000, Postgres 5432. Local frontend dev needs Node 18+ (see [services/frontend/README.md](services/frontend/README.md)). Backend service prerequisites live in their own READMEs under [services/](services/).
- **GCP/GKE (Pulumi):** Requires Node 20+, Pulumi CLI, `gcloud` auth (`gcloud auth login` and `gcloud auth application-default login`), and access to Artifact Registry images. Infrastructure setup is detailed in [infra/README.md](infra/README.md).
- **Secrets:** Ensure DB credentials, JWT keys, and GCP service accounts are available for both local and GKE deployments. TODO: add a consolidated env/secret checklist for every service.
- **Data:** DVC points at `gs://fitai-data-bucket` via `fitai_data_bucket.dvc`; see [docs/data-versioning.md](docs/data-versioning.md). TODO: document the exact `dvc pull` workflow and access requirements.
- Optional references: [docs/model-training.md](docs/model-training.md), service-specific READMEs (e.g., [services/rag-service/README.md](services/rag-service/README.md), [services/core-etl-api/README.md](services/core-etl-api/README.md)), and [docs/UI_Screens.md](docs/UI_Screens.md).

## Deployment instructions
- **Local:** From repo root, run `docker compose up --build -d`; check with `docker compose ps`; stop with `docker compose down -v`. Development- or image-only flows are outlined in each service README (e.g., [services/frontend/README.md](services/frontend/README.md), [services/rag-service/README.md](services/rag-service/README.md)).
- **CD (GitHub Actions):** Push to `main` (or manually trigger the “CD” workflow) to build all service images, push to Artifact Registry, update Pulumi config with new tags, and run `pulumi up` against stack `zih428-org/FitAI_infra/dev`. Required GitHub secrets: `PULUMI_ACCESS_TOKEN`, `GCP_CREDENTIALS_JSON` (service account JSON with Artifact Registry + GKE perms), optional `PULUMI_CONFIG_PASSPHRASE` and any Pulumi config secrets (`dbPassword`, `jwtSecret`, `gcpServiceAccountKey`, etc.).
- **GCP/GKE (Pulumi):** Follow [infra/README.md](infra/README.md) for manual deploys. Common flow: set `PULUMI_HOME`, select the stack (`pulumi stack select zih428-org/FitAI_infra/dev`), ensure images exist in Artifact Registry, then run `pulumi up` after `gcloud` auth. The autoscaled GKE deployment is currently reachable at http://34.71.139.146/login. HPA demo and kubectl commands are documented in [infra/README.md](infra/README.md).

## Usage details and examples
- **Local:** After `docker compose` is running, open http://localhost:3000 (screens in [docs/UI_Screens.md](docs/UI_Screens.md)).
- **GCP/GKE (Pulumi):** Use the load balancer IPs output by Pulumi (see [infra/README.md](infra/README.md)) to reach frontend and APIs. Adjust frontend environment URLs as needed when not running on localhost. TODO: add end-to-end examples for auth + profile + plan generation against deployed load balancers.

## Known issues and limitations
- **Local:** The frontend AI Coach currently hardcodes `http://localhost:8002` for rag-service in [services/frontend/app/ai-coach/page.tsx](services/frontend/app/ai-coach/page.tsx); non-local hosts require code changes or env-driven URLs. TODO: enumerate any flaky local flows or open bugs.
- **GCP/GKE (Pulumi):** Requires access to GCS/Vertex AI/Artifact Registry and production secrets; these are not stored in this repository. TODO: call out any deployment-time pitfalls (e.g., missing images, quota limits) observed in recent runs.